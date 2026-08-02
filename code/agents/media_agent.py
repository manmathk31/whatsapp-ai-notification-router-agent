"""
Media Analyst Agent
Processes images and voice notes using Gemini 3.1 Flash.
Caches results locally so each file is only processed once across all runs.
"""

import json
import os
from pathlib import Path
from pydantic import ValidationError

import config
from models import MediaAnalysis
from data_loader import DataStore

class MediaAgent:
    def __init__(self, data_store: DataStore):
        self.ds = data_store
        
        # Initialize Gemini Client if API key is present
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            from google import genai
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
            
        self.cache_file = config.MEDIA_CACHE_FILE
        self.cache: dict[str, MediaAnalysis] = self._load_cache()

    def _load_cache(self) -> dict[str, MediaAnalysis]:
        if not self.cache_file.exists():
            return {}
        try:
            with open(self.cache_file, "r") as f:
                data = json.load(f)
                return {k: MediaAnalysis(**v) for k, v in data.items()}
        except Exception:
            return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w") as f:
                json.dump({k: v.model_dump() for k, v in self.cache.items()}, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save media cache: {e}")

    def analyze_media(self, media_id: str, media_type: str, file_path: str) -> MediaAnalysis:
        # 1. Return from cache if available
        if media_id in self.cache:
            return self.cache[media_id]

        # 2. Check API key
        if not self.client:
            return MediaAnalysis(
                media_type=media_type,
                description="Analysis unavailable: GEMINI_API_KEY not set",
                extracted_text="",
                content_category="unknown",
                risk_flags=["no_api_key"],
                urgency_level="low"
            )
            
        # 3. Check file existence
        # The file_path from CSV is relative, e.g., 'dataset/media/images/img_001.jpg'
        full_path = config.PROJECT_ROOT / file_path
        if not full_path.exists():
            return MediaAnalysis(
                media_type=media_type,
                description=f"File not found: {file_path}",
                extracted_text="",
                content_category="unknown",
                risk_flags=["file_missing"],
                urgency_level="low"
            )
            
        # 4. Process with Gemini 3.1 Flash
        try:
            # Upload the media file using the google-genai files API
            uploaded_file = self.client.files.upload(file=str(full_path))
            
            if media_type == "image":
                prompt = (
                    "Describe this image concisely. What type of content is it? "
                    "Extract any visible text. Is it a promotional poster, document, "
                    "screenshot, photo, or something else? Note any scam or risk indicators."
                )
            else: # voice note
                prompt = (
                    "Transcribe this voice note. Summarize the content. "
                    "What language is spoken? Is it urgent, casual, or promotional? "
                    "Note any concerning content or tone."
                )
                
            import time
            # Rate limit protection: API allows 16 RPM (1 call every ~3.75s)
            time.sleep(4.0)
            
            # Request structured JSON output
            response = self.client.models.generate_content(
                model=config.MODEL_FLASH,
                contents=[uploaded_file, prompt],
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': MediaAnalysis,
                    'temperature': 0.1
                }
            )
            
            # Clean up the file from Google's servers to save quota
            try:
                self.client.files.delete(name=uploaded_file.name)
            except Exception:
                pass
            
            # Parse response
            try:
                # The google-genai SDK maps JSON output to the pydantic model in response.parsed
                if hasattr(response, 'parsed') and response.parsed:
                    analysis = response.parsed
                else:
                    # Fallback manual parsing if SDK didn't auto-parse
                    analysis_dict = json.loads(response.text)
                    analysis = MediaAnalysis(**analysis_dict)
                    
                self.cache[media_id] = analysis
                self._save_cache()
                return analysis
                
            except Exception as e:
                print(f"Failed to parse model output for {media_id}: {e}")
                return MediaAnalysis(
                    media_type=media_type,
                    description="Parsing failed",
                    extracted_text="",
                    content_category="unknown",
                    risk_flags=["parsing_error"],
                    urgency_level="low"
                )
                
        except Exception as e:
            print(f"API call failed for {media_id}: {e}")
            return MediaAnalysis(
                media_type=media_type,
                description=f"API Error: {str(e)}",
                extracted_text="",
                content_category="unknown",
                risk_flags=["api_error"],
                urgency_level="low"
            )

    def analyze_all_media(self):
        """Batch function to analyze all media in the dataset and populate cache."""
        for m_id, path in self.ds.images_by_id.items():
            self.analyze_media(m_id, "image", path)
            
        for m_id, path in self.ds.voice_notes_by_id.items():
            self.analyze_media(m_id, "voice", path)
            
        return self.cache

"""
Routing Judge Agent (Tier 2 and Tier 3)
Receives structured context from all other agents and makes the final routing decision
using either Gemini 3.1 Flash (routine cases) or Gemini 3.1 Pro (complex cases).
"""

import os
import json
import config
from models import RoutingVerdict, SafetyAssessment, ContextProfile, EvidenceBundle, MediaAnalysis

class JudgeAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            from google import genai
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
            
        config.PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        
        sys_path = config.PROMPTS_DIR / "judge_system.txt"
        few_path = config.PROMPTS_DIR / "judge_fewshot.txt"
        
        self.sys_prompt = sys_path.read_text() if sys_path.exists() else ""
        self.few_shot = few_path.read_text() if few_path.exists() else ""

    def should_use_pro(self, safety: SafetyAssessment, context: ContextProfile, evidence: EvidenceBundle) -> bool:
        """Escalate to Pro model only when genuinely complex (Tier 3)"""
        # Conflicting signals: trusted sender but suspicious content
        if safety.risk_level == "suspicious" and context.sender_trust in ("admin", "trusted"):
            return True
        # Unknown senders with ambiguous intent (needs nuance)
        if context.sender_trust == "unknown" and not safety.risk_flags:
            return True
        # Verified business sending risky content
        if context.business_verified and safety.risk_flags:
            return True
        # Routine cases can be handled by Flash
        return False

    def decide(self, msg: dict, safety: SafetyAssessment, context: ContextProfile, evidence: EvidenceBundle, media: MediaAnalysis = None, model: str = None) -> RoutingVerdict:
        if not self.client:
            return RoutingVerdict(
                message_id=msg["message_id"],
                action="digest",
                message_type="unknown",
                reason="Fallback: No API key provided",
                confidence=0.5,
                evidence_message_ids="none",
                decided_by="fallback"
            )

        if not model:
            model = config.MODEL_PRO if self.should_use_pro(safety, context, evidence) else config.MODEL_FLASH

        # Construct the context payload
        prompt = f"""
## Message to Route
ID: {msg.get('message_id')}
Type: {msg.get('conversation_type')}
Sender: {msg.get('sender_user_id') or msg.get('business_id')}
Content: {msg.get('message_text')}

## Safety Assessment
Risk Level: {safety.risk_level}
Flags: {safety.risk_flags}
Prompt Injection: {safety.is_prompt_injection}

## Personalized Context
User Engagement: {context.user_engagement}
Sender Trust: {context.sender_trust}
Group Type: {context.group_type}
Business Relationship: {context.business_relationship}
Fatigue: {context.notification_fatigue}
Direct Mention: {context.is_direct_mention}
During DND: {context.is_during_dnd}

## Historical Evidence
Evidence IDs: {evidence.evidence_ids}
Reasons: {evidence.evidence_reasons}
User Reaction Pattern: {evidence.user_reaction_pattern}
"""
        if media:
            prompt += f"\n## Media Analysis\nType: {media.media_type}\nDescription/Text: {media.description}\n{media.extracted_text}\nRisk Flags: {media.risk_flags}\n"

        prompt += "\nDecide: action, message_type, reason, confidence, evidence_message_ids"

        full_system_instruction = self.sys_prompt + "\n\n" + self.few_shot

        try:
            import time
            # Rate limit protection: API allows 16 RPM (1 call every ~3.75s)
            time.sleep(4.0)
            
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    'system_instruction': full_system_instruction,
                    'response_mime_type': 'application/json',
                    'response_schema': RoutingVerdict,
                    'temperature': 0.1
                }
            )
            
            # Parse output
            if hasattr(response, 'parsed') and response.parsed:
                verdict = response.parsed
            else:
                v_dict = json.loads(response.text)
                verdict = RoutingVerdict(**v_dict)
                
            # Guarantee consistency
            verdict.message_id = msg["message_id"]
            if verdict.evidence_message_ids is None or str(verdict.evidence_message_ids).strip() == "":
                verdict.evidence_message_ids = "none"
            verdict.decided_by = config.TIER_PRO if model == config.MODEL_PRO else config.TIER_FLASH
            
            return verdict
            
        except Exception as e:
            print(f"LLM failure for {msg['message_id']}: {e}")
            return RoutingVerdict(
                message_id=msg["message_id"],
                action="digest",
                message_type="unknown",
                reason=f"LLM Error: {str(e)}",
                confidence=0.5,
                evidence_message_ids="none",
                decided_by="error_fallback"
            )

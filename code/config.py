"""
Configuration for the Message Notification Router.

Central configuration file containing all paths, model names, allowed values,
and environment variable management. All other modules import from here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# ---------------------------------------------------------------------------
# API Configuration
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_FLASH = "gemini-3.5-flash-lite"       # High rate limit (15 RPM) - Used for routine cases
MODEL_PRO = "gemini-3.5-flash-lite"         # Same model used to avoid 0 RPM quota on Pro tier

# ---------------------------------------------------------------------------
# Paths — All relative to the project root (parent of code/)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
MEDIA_DIR = DATASET_DIR / "media"
IMAGES_DIR = MEDIA_DIR / "images"
AUDIO_DIR = MEDIA_DIR / "audio"
OUTPUT_CSV = DATASET_DIR / "output.csv"

# Dataset files
MESSAGES_CSV = DATASET_DIR / "messages.csv"
SAMPLE_MESSAGES_CSV = DATASET_DIR / "sample_messages.csv"
USERS_CSV = DATASET_DIR / "users.csv"
GROUPS_CSV = DATASET_DIR / "groups.csv"
GROUP_MEMBERS_CSV = DATASET_DIR / "group_members.csv"
BUSINESS_ACCOUNTS_CSV = DATASET_DIR / "business_accounts.csv"
USER_BUSINESS_HISTORY_CSV = DATASET_DIR / "user_business_history.csv"
MESSAGE_HISTORY_CSV = DATASET_DIR / "message_history.csv"
MESSAGE_EVENTS_CSV = DATASET_DIR / "message_events.csv"
IMAGES_CSV = DATASET_DIR / "images.csv"
VOICE_NOTES_CSV = DATASET_DIR / "voice_notes.csv"
DAILY_NOTIFICATION_SUMMARY_CSV = DATASET_DIR / "daily_notification_summary.csv"

# Cache
MEDIA_CACHE_FILE = Path(__file__).resolve().parent / "media_cache.json"

# Prompts
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# ---------------------------------------------------------------------------
# Allowed Values (from problem_statement.md)
# ---------------------------------------------------------------------------
ALLOWED_ACTIONS = ["notify", "digest", "mute"]

ALLOWED_MESSAGE_TYPES = [
    "personal",
    "urgent",
    "event",
    "payment",
    "business_update",
    "promotion",
    "greeting",
    "forward",
    "spam",
    "scam",
    "unknown",
]

# ---------------------------------------------------------------------------
# Output CSV Column Order (must match exactly)
# ---------------------------------------------------------------------------
OUTPUT_COLUMNS = [
    "message_id",
    "action",
    "message_type",
    "reason",
    "confidence",
    "evidence_message_ids",
]

# ---------------------------------------------------------------------------
# Tier Labels (for tracking which tier decided each message)
# ---------------------------------------------------------------------------
TIER_RULE_ENGINE = "rule_engine"
TIER_FLASH = "flash_agent"
TIER_PRO = "pro_judge"

"""
Pydantic data models for the Message Notification Router.
These define the strict contracts for inter-agent communication.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class SafetyAssessment(BaseModel):
    risk_level: str = Field(description="'safe' | 'suspicious' | 'dangerous'")
    risk_flags: List[str] = Field(description="List of identified risk flags, e.g. ['domain_mismatch', 'otp_harvesting']")
    is_prompt_injection: bool = Field(description="Whether the message attempts prompt injection")
    scam_type: Optional[str] = Field(description="Specific type of scam if applicable, e.g., 'phishing', 'fake_urgency'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    can_resolve: bool = Field(description="True if Tier 1 (rules) can decide this without LLM")

class ContextProfile(BaseModel):
    user_engagement: str = Field(description="'high' | 'medium' | 'low' | 'dismissive'")
    sender_trust: str = Field(description="'admin' | 'trusted' | 'known' | 'unknown' | 'suspicious'")
    is_direct_mention: bool = Field(description="True if the message mentions the user directly")
    is_during_dnd: bool = Field(description="True if the message is received during DND window")
    group_type: Optional[str] = Field(description="The type of group if it's a group message")
    user_muted_group: bool = Field(description="True if the user has muted this group")
    business_verified: Optional[bool] = Field(description="True if it's a verified business")
    business_relationship: Optional[str] = Field(description="E.g., 'active_order', 'opted_out', 'no_history'")
    notification_fatigue: str = Field(description="'low' | 'moderate' | 'high'")

class EvidenceBundle(BaseModel):
    evidence_ids: List[str] = Field(description="Up to 3 relevant historical message IDs")
    evidence_reasons: List[str] = Field(description="Why these messages are relevant")
    user_reaction_pattern: str = Field(description="'engaged', 'ignored', 'dismissed', 'reported'")
    similar_content_action: Optional[str] = Field(description="What the user did with similar past content")

class MediaAnalysis(BaseModel):
    media_type: str = Field(description="'image' | 'voice'")
    description: str = Field(description="Description of what the media contains")
    extracted_text: str = Field(description="OCR text or voice transcription")
    content_category: str = Field(description="E.g., 'promotional', 'document', 'photo', 'scam'")
    risk_flags: List[str] = Field(description="Risk flags identified in the media")
    urgency_level: str = Field(description="'high' | 'medium' | 'low'")

class RoutingVerdict(BaseModel):
    message_id: str = Field(description="The ID of the message being routed")
    action: str = Field(description="'notify' | 'digest' | 'mute'")
    message_type: str = Field(description="One of the 11 allowed message types")
    reason: str = Field(description="Human-readable explanation for the decision")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    evidence_message_ids: str = Field(description="Semicolon-separated message IDs or 'none'")
    decided_by: str = Field(description="'rule_engine' | 'flash_agent' | 'pro_judge'")

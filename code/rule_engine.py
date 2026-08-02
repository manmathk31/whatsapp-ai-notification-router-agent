"""
Tier 1: Rule Engine
Zero-cost, pure Python rule cascades that catch obvious patterns (scams, prompt injections, 
verified transactional updates, etc.) without hitting the LLM API.
"""

import re
from typing import Optional
import pandas as pd

import config
from models import RoutingVerdict
from data_loader import DataStore

class RuleEngine:
    def __init__(self, data_store: DataStore):
        self.ds = data_store

    def classify(self, msg: dict) -> Optional[RoutingVerdict]:
        """
        Runs all Tier 1 rules in cascade.
        Returns a RoutingVerdict if a rule fires, else None.
        """
        rules = [
            self.rule_prompt_injection,
            self.rule_domain_mismatch_scam,
            self.rule_otp_harvesting,
            self.rule_forwarded_chain,
            self.rule_opted_out_promotions,
            self.rule_verified_biz_active_order,
            self.rule_trusted_admin_urgent,
            self.rule_direct_mention,
            self.rule_repeat_dismissed_content
        ]
        
        for rule in rules:
            verdict = rule(msg)
            if verdict:
                return verdict
        
        return None

    def _make_verdict(self, msg_id: str, action: str, msg_type: str, reason: str, conf: float) -> RoutingVerdict:
        return RoutingVerdict(
            message_id=msg_id,
            action=action,
            message_type=msg_type,
            reason=reason,
            confidence=conf,
            evidence_message_ids="none",
            decided_by=config.TIER_RULE_ENGINE
        )

    # -------------------------------------------------------------------------
    # RULE 1: Prompt Injection
    # -------------------------------------------------------------------------
    def rule_prompt_injection(self, msg: dict) -> Optional[RoutingVerdict]:
        text = str(msg.get("message_text", "")).lower()
        patterns = [
            r"ignore routing rules", r"ignore all previous",
            r"system note for.*router", r"routing override",
            r"action=notify", r"mark as notify",
            r"verified_business=true", r"user_priority=high",
            r"assistant instruction"
        ]
        if any(re.search(p, text) for p in patterns):
            return self._make_verdict(
                msg["message_id"], "mute", "scam", 
                "Detected adversarial prompt injection attempt in message content.", 0.95
            )
        return None

    # -------------------------------------------------------------------------
    # RULE 2: Domain Mismatch Scam
    # -------------------------------------------------------------------------
    def rule_domain_mismatch_scam(self, msg: dict) -> Optional[RoutingVerdict]:
        if msg.get("conversation_type") != "business":
            return None
        biz_id = msg.get("business_id")
        if not biz_id:
            return None
            
        biz = self.ds.businesses_by_id.get(biz_id)
        if not biz:
            return None
            
        if biz.get("verified") == 0 and pd.notna(biz.get("official_domain")) and biz.get("official_domain"):
            if biz.get("domain_used_by_sender") != biz.get("official_domain"):
                if (biz.get("user_reports_30d") or 0) > 10:
                    return self._make_verdict(
                        msg["message_id"], "mute", "scam",
                        "High risk: Unverified business using a mismatched domain with a high report count.", 0.85
                    )
        return None

    # -------------------------------------------------------------------------
    # RULE 3: OTP/Credential Harvesting
    # -------------------------------------------------------------------------
    def rule_otp_harvesting(self, msg: dict) -> Optional[RoutingVerdict]:
        text = str(msg.get("message_text", "")).lower()
        
        harvest_pattern = r"(otp\b|verification code|password|pin\b|bank details|login code)"
        urgency_pattern = r"(immediately|now|today|expires|blocked|locked|suspend)"
        
        if re.search(harvest_pattern, text) and re.search(urgency_pattern, text):
            # Check if it's a verified business with matching domain
            is_legit = False
            if msg.get("conversation_type") == "business":
                biz_id = msg.get("business_id")
                biz = self.ds.businesses_by_id.get(biz_id, {})
                if biz.get("verified") == 1 and biz.get("domain_used_by_sender") == biz.get("official_domain"):
                    is_legit = True
            
            if not is_legit:
                return self._make_verdict(
                    msg["message_id"], "mute", "scam",
                    "Suspicious request for credentials/OTP with fake urgency from an unverified sender.", 0.83
                )
        return None

    # -------------------------------------------------------------------------
    # RULE 4: Forwarded Chain Messages
    # -------------------------------------------------------------------------
    def rule_forwarded_chain(self, msg: dict) -> Optional[RoutingVerdict]:
        fwd_count = msg.get("forwarded_count") or 0
        if pd.notna(fwd_count) and float(fwd_count) >= 5:
            text = str(msg.get("message_text", "")).lower()
            chain_patterns = [
                r"forward to", r"share with", r"don't break the chain",
                r"good luck", r"blessings", r"share in.*groups"
            ]
            if any(re.search(p, text) for p in chain_patterns):
                return self._make_verdict(
                    msg["message_id"], "mute", "forward",
                    "Highly forwarded chain message exhibiting typical spam or blessing patterns.", 0.83
                )
        return None

    # -------------------------------------------------------------------------
    # RULE 5: Opted-out Business Promotions
    # -------------------------------------------------------------------------
    def rule_opted_out_promotions(self, msg: dict) -> Optional[RoutingVerdict]:
        if msg.get("conversation_type") == "business":
            user_id = msg.get("user_id")
            biz_id = msg.get("business_id")
            rel = self.ds.user_biz_index.get((user_id, biz_id))
            
            if rel and rel.get("allows_promotions") == 0 and pd.notna(rel.get("promotions_opted_out_at")):
                text = str(msg.get("message_text", "")).lower()
                promo_words = ["coupon", "discount", "offer", "sale", "deal", "cashback"]
                if any(w in text for w in promo_words):
                    return self._make_verdict(
                        msg["message_id"], "mute", "promotion",
                        "The user explicitly opted out of promotional messages from this business.", 0.90
                    )
        return None

    # -------------------------------------------------------------------------
    # RULE 6: Verified Biz + Active Order
    # -------------------------------------------------------------------------
    def rule_verified_biz_active_order(self, msg: dict) -> Optional[RoutingVerdict]:
        if msg.get("conversation_type") == "business":
            user_id = msg.get("user_id")
            biz_id = msg.get("business_id")
            biz = self.ds.businesses_by_id.get(biz_id, {})
            rel = self.ds.user_biz_index.get((user_id, biz_id), {})
            
            if biz.get("verified") == 1 and biz.get("domain_used_by_sender") == biz.get("official_domain"):
                why = str(rel.get("why_user_knows", "")).lower()
                if any(k in why for k in ["active", "upcoming", "recent", "expected"]):
                    text = str(msg.get("message_text", "")).lower()
                    promo_words = ["coupon", "discount", "offer", "sale", "deal"]
                    if not any(w in text for w in promo_words):
                        # Transactional update
                        return self._make_verdict(
                            msg["message_id"], "notify", "business_update",
                            "Transactional update from a verified business regarding an active order or booking.", 0.89
                        )
        return None

    # -------------------------------------------------------------------------
    # RULE 7: Trusted Admin + Time-Sensitive
    # -------------------------------------------------------------------------
    def rule_trusted_admin_urgent(self, msg: dict) -> Optional[RoutingVerdict]:
        if msg.get("conversation_type") == "group":
            user_id = msg.get("user_id")
            group_id = msg.get("group_id")
            sender_id = msg.get("sender_user_id")
            
            # Check if user mutes this group
            user_membership = self.ds.group_members_index.get((user_id, group_id), {})
            if user_membership.get("group_muted_by_user") == 1:
                return None
                
            sender_membership = self.ds.group_members_index.get((sender_id, group_id), {})
            if sender_membership.get("role") == "admin":
                text = str(msg.get("message_text", "")).lower()
                urgent_words = [r"\bnow\b", r"\btoday\b", r"\bminutes\b", r"\bimmediately\b", r"before .* pm", r"leaving in", r"closes at", r"\bdeadline\b"]
                if any(re.search(w, text) for w in urgent_words):
                    return self._make_verdict(
                        msg["message_id"], "notify", "urgent",
                        "Time-sensitive update from a recognized group admin.", 0.87
                    )
        return None

    # -------------------------------------------------------------------------
    # RULE 8: Direct @mention
    # -------------------------------------------------------------------------
    def rule_direct_mention(self, msg: dict) -> Optional[RoutingVerdict]:
        user_id = msg.get("user_id")
        if not user_id: return None
        
        text = str(msg.get("message_text", "")).lower()
        if f"@{user_id}".lower() in text:
            action_words = [r"\bcall\b", r"\bcheck\b", r"\bjoin\b", r"\bsend\b", r"\bcome\b", r"\bplease\b", r"\burly\b", r"\bnow\b"]
            if any(re.search(w, text) for w in action_words):
                return self._make_verdict(
                    msg["message_id"], "notify", "personal",
                    "Direct mention requiring immediate user attention or action.", 0.85
                )
        return None

    # -------------------------------------------------------------------------
    # RULE 9: Repeat Dismissed Content
    # -------------------------------------------------------------------------
    def rule_repeat_dismissed_content(self, msg: dict) -> Optional[RoutingVerdict]:
        user_id = msg.get("user_id")
        sender_id = msg.get("sender_user_id")
        if not sender_id or not user_id:
            return None
            
        history = self.ds.history_by_sender_user.get((sender_id, user_id), [])
        if not history:
            return None
            
        text = str(msg.get("message_text", "")).lower()
        if len(text) < 15: # Too short to reliably match repeats
            return None
            
        dismissed_count = 0
        for h in history:
            h_text = str(h.get("message_text", "")).lower()
            if text == h_text or text[:30] in h_text:
                events = self.ds.events_by_msg.get(h.get("message_id"), [])
                for e in events:
                    if e.get("event_type") in ["notification_dismissed", "muted"]:
                        dismissed_count += 1
                        break # count once per message
                        
        if dismissed_count >= 2: 
            return self._make_verdict(
                msg["message_id"], "mute", "spam",
                "User has repeatedly dismissed or muted highly similar content from this sender.", 0.82
            )
            
        return None

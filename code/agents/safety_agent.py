"""
Safety Guardian Agent
Assesses scam, spam, phishing, and adversarial prompt injections that weren't obvious
enough for the Tier 1 Rule Engine. Provides risk scoring for the LLM Judge.
"""

import pandas as pd
from models import SafetyAssessment
from data_loader import DataStore

class SafetyAgent:
    def __init__(self, data_store: DataStore):
        self.ds = data_store

    def assess(self, msg: dict) -> SafetyAssessment:
        risk_flags = []
        is_prompt_injection = False
        scam_type = None
        risk_level = "safe"
        
        text = str(msg.get("message_text", "")).lower()
        
        # 1. Advanced check for prompt injection
        injection_patterns = ["ignore routing rules", "system note for router", "routing override", "action=notify", "assistant instruction", "ignore sender risk"]
        if any(p in text for p in injection_patterns):
            is_prompt_injection = True
            risk_flags.append("prompt_injection")
            risk_level = "dangerous"
            scam_type = "adversarial_attack"

        # 2. Check business legitimacy
        if msg.get("conversation_type") == "business":
            biz_id = msg.get("business_id")
            biz = self.ds.businesses_by_id.get(biz_id, {})
            
            if biz.get("verified") == 0:
                risk_flags.append("unverified_business")
                
                # Domain mismatch
                off_dom = biz.get("official_domain")
                used_dom = biz.get("domain_used_by_sender")
                if pd.notna(off_dom) and off_dom:
                    if used_dom != off_dom:
                        risk_flags.append("domain_mismatch")
                        risk_level = "suspicious" if risk_level == "safe" else risk_level
                        scam_type = "phishing"
                
                # High reports or young account
                reports = biz.get("user_reports_30d") or 0
                age = biz.get("account_age_days") or 999
                
                if reports > 10 or age < 40:
                    risk_flags.append("high_reports_or_new")
                    if reports > 50:
                        risk_level = "dangerous"
                        
        # 3. Suspicious URLs (e.g. shortlinks or hyphenated domains mimicking brands)
        url_patterns = ["bit.ly/", "vl.gl/", "weurl.co/", "shorturl.at/"]
        if any(u in text for u in url_patterns):
            risk_flags.append("suspicious_shortlink")
            risk_level = "suspicious" if risk_level == "safe" else risk_level
            
        # 4. Text heuristics for credential harvesting
        harvest_pattern = ["otp", "verification code", "password", "pin", "bank details"]
        if any(w in text for w in harvest_pattern):
            risk_flags.append("credential_request")
            risk_level = "suspicious" if risk_level == "safe" else risk_level
            
        return SafetyAssessment(
            risk_level=risk_level,
            risk_flags=risk_flags,
            is_prompt_injection=is_prompt_injection,
            scam_type=scam_type,
            confidence=0.85,
            can_resolve=False  # Tier 2/3 will use this
        )

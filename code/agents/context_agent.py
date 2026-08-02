"""
Context Intelligence Agent
Builds a rich, personalized profile of the message context: sender trust, user engagement,
notification fatigue, group dynamics, and business relationships.
"""

import datetime
import pandas as pd
from models import ContextProfile
from data_loader import DataStore

class ContextAgent:
    def __init__(self, data_store: DataStore):
        self.ds = data_store

    def _is_in_dnd(self, msg_time_str: str, dnd_str: str) -> bool:
        if pd.isna(msg_time_str) or pd.isna(dnd_str) or not dnd_str or "-" not in dnd_str:
            return False
        try:
            # Parse message time (e.g., "2026-08-01T14:30:00Z")
            msg_dt = datetime.datetime.strptime(msg_time_str, "%Y-%m-%dT%H:%M:%SZ")
            msg_t = msg_dt.time()
            
            # Parse DND window (e.g., "22:00-07:00")
            start_s, end_s = dnd_str.split("-")
            start_t = datetime.datetime.strptime(start_s.strip(), "%H:%M").time()
            end_t = datetime.datetime.strptime(end_s.strip(), "%H:%M").time()
            
            if start_t <= end_t:
                return start_t <= msg_t <= end_t
            else:
                return msg_t >= start_t or msg_t <= end_t
        except:
            return False

    def build_profile(self, msg: dict) -> ContextProfile:
        user_id = msg.get("user_id")
        user = self.ds.users_by_id.get(user_id, {})
        
        # 1. User engagement
        opened = user.get("messages_opened_30d") or 0
        dismissed = user.get("notifications_dismissed_30d") or 0
        
        total = opened + dismissed
        open_rate = opened / total if total > 0 else 0
        
        if dismissed > 50 and open_rate < 0.2:
            engagement = "dismissive"
        elif open_rate > 0.7:
            engagement = "high"
        elif open_rate > 0.3:
            engagement = "medium"
        else:
            engagement = "low"
            
        # 2. DND Check
        is_dnd = self._is_in_dnd(msg.get("created_at"), user.get("do_not_disturb_window"))
        
        # 3. Direct Mention
        text = str(msg.get("message_text", "")).lower()
        is_mention = False
        if user_id:
            is_mention = f"@{user_id}".lower() in text
        
        # 4. Sender Trust & Group Dynamics
        sender_trust = "unknown"
        sender_id = msg.get("sender_user_id")
        group_id = msg.get("group_id")
        group_type = None
        user_muted_group = False
        
        if group_id:
            group = self.ds.groups_by_id.get(group_id, {})
            group_type = group.get("group_type")
            user_membership = self.ds.group_members_index.get((user_id, group_id), {})
            user_muted_group = (user_membership.get("group_muted_by_user") == 1)
            
            if sender_id:
                sender_membership = self.ds.group_members_index.get((sender_id, group_id), {})
                if sender_membership.get("role") == "admin":
                    sender_trust = "admin"
                    
        if sender_trust == "unknown" and sender_id:
            history = self.ds.history_by_sender_user.get((sender_id, user_id), [])
            if len(history) > 5:
                sender_trust = "trusted"
            elif len(history) > 0:
                sender_trust = "known"
                
        # 5. Business Relationship
        biz_verified = None
        biz_rel = None
        if msg.get("conversation_type") == "business":
            biz_id = msg.get("business_id")
            biz = self.ds.businesses_by_id.get(biz_id, {})
            biz_verified = (biz.get("verified") == 1)
            
            rel = self.ds.user_biz_index.get((user_id, biz_id), {})
            if rel:
                biz_rel = rel.get("why_user_knows", "historical_interaction")
                if rel.get("allows_promotions") == 0:
                    biz_rel = "opted_out"
            else:
                biz_rel = "no_history"
                
        # 6. Notification Fatigue
        fatigue = "low"
        daily = self.ds.daily_notif_by_user.get(user_id, [])
        if daily:
            avg_rcv = sum(d.get("notifications_received") or 0 for d in daily) / len(daily)
            if avg_rcv > 50:
                fatigue = "high"
            elif avg_rcv > 20:
                fatigue = "moderate"
        
        return ContextProfile(
            user_engagement=engagement,
            sender_trust=sender_trust,
            is_direct_mention=is_mention,
            is_during_dnd=is_dnd,
            group_type=group_type,
            user_muted_group=user_muted_group,
            business_verified=biz_verified,
            business_relationship=biz_rel,
            notification_fatigue=fatigue
        )

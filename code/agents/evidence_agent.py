"""
Evidence Retriever Agent
Finds the most relevant historical messages and user reactions to provide 
concrete behavioral evidence for the routing decision.
"""

from models import EvidenceBundle
from data_loader import DataStore

class EvidenceAgent:
    def __init__(self, data_store: DataStore):
        self.ds = data_store

    def find_evidence(self, msg: dict) -> EvidenceBundle:
        user_id = msg.get("user_id")
        sender_id = msg.get("sender_user_id")
        biz_id = msg.get("business_id")
        text = str(msg.get("message_text", "")).lower()
        
        evidence_ids = []
        evidence_reasons = []
        pattern = "ignored"
        sim_action = None
        
        candidates = []
        
        # 1. Exact sender matches
        if sender_id:
            candidates.extend(self.ds.history_by_sender_user.get((sender_id, user_id), []))
            
        # 2. Business matches
        if biz_id:
            candidates.extend(self.ds.history_by_business_user.get((biz_id, user_id), []))
            
        # 3. Score candidates by relevance
        scored = []
        for c in candidates:
            c_text = str(c.get("message_text", "")).lower()
            score = 0
            
            # Content similarity is strongest signal
            if c_text == text:
                score = 100
            elif len(text) > 10 and text[:20] in c_text:
                score = 50
            elif sender_id and c.get("sender_user_id") == sender_id:
                score = 10
            elif biz_id and c.get("business_id") == biz_id:
                score = 10
                
            scored.append((score, c))
            
        # 4. Sort and take top 3
        scored.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [c for s, c in scored[:3] if s > 0]
        
        if top_candidates:
            for c in top_candidates:
                m_id = c.get("message_id")
                evidence_ids.append(m_id)
                
                # Fetch events to see how user reacted
                events = self.ds.events_by_msg.get(m_id, [])
                
                reaction = "ignored"
                for e in events:
                    e_type = e.get("event_type")
                    if e_type == "notification_dismissed":
                        reaction = "dismissed"
                    elif e_type == "muted":
                        reaction = "muted"
                    elif e_type == "message_opened":
                        reaction = "opened"
                    elif e_type == "replied":
                        reaction = "replied"
                    elif e_type == "reported_spam":
                        reaction = "reported"
                
                evidence_reasons.append(f"Historical msg {m_id} reacted as: {reaction}")
                
                # Aggregate pattern
                if reaction in ["muted", "reported", "dismissed"]:
                    pattern = "dismissed"
                    sim_action = "user disliked"
                elif reaction in ["opened", "replied"]:
                    pattern = "engaged"
                    sim_action = "user engaged"
                    
        return EvidenceBundle(
            evidence_ids=evidence_ids,
            evidence_reasons=evidence_reasons,
            user_reaction_pattern=pattern,
            similar_content_action=sim_action
        )

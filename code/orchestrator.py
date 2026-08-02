"""
Main Orchestrator
Coordinates the 3-tier routing funnel. Dispatches messages to the Rule Engine, 
builds context via specialist agents, and calls the Judge Agent for unresolved cases.
"""

from models import RoutingVerdict
from data_loader import DataStore
from rule_engine import RuleEngine
from agents.safety_agent import SafetyAgent
from agents.context_agent import ContextAgent
from agents.evidence_agent import EvidenceAgent
from agents.judge_agent import JudgeAgent

class Orchestrator:
    def __init__(self, ds: DataStore):
        self.ds = ds
        self.rule_engine = RuleEngine(ds)
        self.safety = SafetyAgent(ds)
        self.context = ContextAgent(ds)
        self.evidence = EvidenceAgent(ds)
        self.judge = JudgeAgent()

    def process_message(self, msg: dict, media_cache: dict) -> RoutingVerdict:
        # Tier 1: Rules (Zero Cost)
        verdict = self.rule_engine.classify(msg)
        if verdict:
            return verdict
            
        # Build Context (Pure Python)
        safety_assessment = self.safety.assess(msg)
        context_profile = self.context.build_profile(msg)
        evidence_bundle = self.evidence.find_evidence(msg)
        
        # Look up cached media analysis
        media_analysis = None
        if msg.get("media_id"):
            media_analysis = media_cache.get(msg.get("media_id"))
            
        # Tier 2/3: LLM Judge (Flash or Pro)
        verdict = self.judge.decide(
            msg=msg, 
            safety=safety_assessment, 
            context=context_profile, 
            evidence=evidence_bundle, 
            media=media_analysis
        )
        
        return verdict

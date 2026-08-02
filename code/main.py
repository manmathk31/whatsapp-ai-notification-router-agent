"""
Entry point for the Message Notification Router.
Loads data, initializes agents, runs the orchestrator, and writes output.csv.
"""

import sys
import pandas as pd
from pathlib import Path

import config
import data_loader
from orchestrator import Orchestrator
from agents.media_agent import MediaAgent

def write_output(verdicts, path):
    rows = []
    for v in verdicts:
        rows.append({
            "message_id": v.message_id,
            "action": v.action,
            "message_type": v.message_type,
            "reason": v.reason,
            "confidence": round(v.confidence, 4),
            "evidence_message_ids": v.evidence_message_ids
        })
    df = pd.DataFrame(rows)
    # Ensure correct column order per specifications
    df = df[config.OUTPUT_COLUMNS] 
    
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\n[+] Wrote {len(df)} predictions to {out_path}")

def main():
    print("="*60)
    print("HackerRank Orchestrate - Message Notification Router")
    print("="*60)
    
    print("\n[1] Loading datasets...")
    ds = data_loader.load_all()
    print(f"    Loaded {len(ds.messages)} messages to route.")
    print(f"    Loaded {len(ds.users_by_id)} users and {len(ds.businesses_by_id)} businesses.")
    
    print("\n[2] Pre-analyzing media files (cached)...")
    media_agent = MediaAgent(ds)
    media_cache = media_agent.analyze_all_media()
    print(f"    Loaded {len(media_cache)} media analyses from cache.")
    
    print("\n[3] Initializing orchestration pipeline...")
    orchestrator = Orchestrator(ds)
    
    verdicts = []
    stats = {
        config.TIER_RULE_ENGINE: 0, 
        config.TIER_FLASH: 0, 
        config.TIER_PRO: 0, 
        "fallback": 0, 
        "error_fallback": 0
    }
    
    print("\n[4] Processing messages...")
    total = len(ds.messages)
    for i, msg in enumerate(ds.messages):
        v = orchestrator.process_message(msg, media_cache)
        verdicts.append(v)
        
        tier = v.decided_by
        stats[tier] = stats.get(tier, 0) + 1
        
        if (i + 1) % 10 == 0 or (i + 1) == total:
            print(f"    Processed {i + 1}/{total} messages...")
            
    print("\n[5] Saving results...")
    write_output(verdicts, config.OUTPUT_CSV)
    
    print("\n[+] Pipeline Complete! Tier distribution:")
    for tier, count in stats.items():
        if count > 0:
            print(f"    - {tier}: {count} messages")
            
    print("="*60)

if __name__ == "__main__":
    main()

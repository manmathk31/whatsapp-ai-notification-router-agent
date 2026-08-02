"""
Evaluation Script (Phase 6)
Runs the orchestrator on the sample_messages.csv dataset and scores the predictions.
"""

import sys
from pathlib import Path

# Add project root to path so we can import from code
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "code"))

import config
import data_loader
from orchestrator import Orchestrator

def evaluate():
    print("="*60)
    print("Evaluating predictions against sample_messages.csv...")
    print("="*60)
    
    # Load all data
    ds = data_loader.load_all()
    orchestrator = Orchestrator(ds)
    media_cache = {} 
    
    if not ds.sample_messages:
        print("Error: No sample messages found.")
        return
        
    correct_action = 0
    correct_type = 0
    total = len(ds.sample_messages)
    
    mismatches = []
    
    for i, msg in enumerate(ds.sample_messages, 1):
        print(f"Processing sample {i}/{total}...", end="\r")
        true_action = str(msg.get("action")).lower()
        true_type = str(msg.get("message_type")).lower()
        
        # Run our system on the sample message
        pred = orchestrator.process_message(msg, media_cache)
        
        if pred.action.lower() == true_action:
            correct_action += 1
        else:
            mismatches.append((msg, pred))
            
        if pred.message_type.lower() == true_type:
            correct_type += 1
            
    print(f"\n\nAccuracy Results (Tested on {total} sample messages):")
    print(f"-> Routing Action Accuracy: {correct_action}/{total} ({correct_action/total*100:.1f}%)")
    print(f"-> Message Type Accuracy:   {correct_type}/{total} ({correct_type/total*100:.1f}%)")
    
    if mismatches:
        print("\n--- Mismatches (Where we got the routing action wrong) ---")
        for msg, pred in mismatches:
            print(f"\nID: {msg.get('message_id')}")
            print(f"Expected: {msg.get('action')}  |  We Predicted: {pred.action}")
            print(f"Our Reason: {pred.reason}")
            print(f"Text snippet: {str(msg.get('message_text'))[:80]}...")
    else:
        print("\nPerfect routing score on the sample set! 🎉")

if __name__ == "__main__":
    evaluate()

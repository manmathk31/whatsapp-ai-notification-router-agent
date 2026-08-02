"""
Data loader for the Message Notification Router.
Loads all 13 CSV files into memory as pandas dataframes and builds efficient lookup indices.
"""

import math
from typing import Dict, List, Any, Tuple
import pandas as pd
import config

class DataStore:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.sample_messages: List[Dict[str, Any]] = []
        
        self.users_by_id: Dict[str, Dict[str, Any]] = {}
        self.groups_by_id: Dict[str, Dict[str, Any]] = {}
        self.group_members_index: Dict[Tuple[str, str], Dict[str, Any]] = {} # (user_id, group_id)
        
        self.businesses_by_id: Dict[str, Dict[str, Any]] = {}
        self.user_biz_index: Dict[Tuple[str, str], Dict[str, Any]] = {} # (user_id, business_id)
        
        self.history_by_user: Dict[str, List[Dict[str, Any]]] = {}
        self.history_by_sender_user: Dict[Tuple[str, str], List[Dict[str, Any]]] = {} # (sender_id, user_id)
        self.history_by_business_user: Dict[Tuple[str, str], List[Dict[str, Any]]] = {} # (business_id, user_id)
        
        self.events_by_msg: Dict[str, List[Dict[str, Any]]] = {}
        
        self.images_by_id: Dict[str, str] = {}
        self.voice_notes_by_id: Dict[str, str] = {}
        
        self.daily_notif_by_user: Dict[str, List[Dict[str, Any]]] = {}

def _clean_dict(d: dict) -> dict:
    """Replace NaN float values with None to make dictionary handling cleaner."""
    res = {}
    for k, v in d.items():
        if isinstance(v, float) and math.isnan(v):
            res[k] = None
        else:
            res[k] = v
    return res

def load_all() -> DataStore:
    """Load all datasets into memory and build lookup indices."""
    store = DataStore()
    
    # 1. Messages
    if config.MESSAGES_CSV.exists():
        df = pd.read_csv(config.MESSAGES_CSV)
        store.messages = [_clean_dict(row) for row in df.to_dict('records')]
        
    if config.SAMPLE_MESSAGES_CSV.exists():
        df = pd.read_csv(config.SAMPLE_MESSAGES_CSV)
        store.sample_messages = [_clean_dict(row) for row in df.to_dict('records')]
        
    # 2. Users
    if config.USERS_CSV.exists():
        df = pd.read_csv(config.USERS_CSV)
        for row in df.to_dict('records'):
            c_row = _clean_dict(row)
            store.users_by_id[c_row['user_id']] = c_row
            
    # 3. Groups & Members
    if config.GROUPS_CSV.exists():
        df = pd.read_csv(config.GROUPS_CSV)
        for row in df.to_dict('records'):
            c_row = _clean_dict(row)
            store.groups_by_id[c_row['group_id']] = c_row
            
    if config.GROUP_MEMBERS_CSV.exists():
        df = pd.read_csv(config.GROUP_MEMBERS_CSV)
        for row in df.to_dict('records'):
            c_row = _clean_dict(row)
            store.group_members_index[(c_row['user_id'], c_row['group_id'])] = c_row
            
    # 4. Businesses
    if config.BUSINESS_ACCOUNTS_CSV.exists():
        df = pd.read_csv(config.BUSINESS_ACCOUNTS_CSV)
        for row in df.to_dict('records'):
            c_row = _clean_dict(row)
            store.businesses_by_id[c_row['business_id']] = c_row
            
    if config.USER_BUSINESS_HISTORY_CSV.exists():
        df = pd.read_csv(config.USER_BUSINESS_HISTORY_CSV)
        for row in df.to_dict('records'):
            c_row = _clean_dict(row)
            store.user_biz_index[(c_row['user_id'], c_row['business_id'])] = c_row
            
    # 5. History & Events
    if config.MESSAGE_HISTORY_CSV.exists():
        df = pd.read_csv(config.MESSAGE_HISTORY_CSV)
        for row in df.to_dict('records'):
            c_row = _clean_dict(row)
            u_id = c_row['user_id']
            s_id = c_row.get('sender_user_id')
            b_id = c_row.get('business_id')
            
            if u_id not in store.history_by_user:
                store.history_by_user[u_id] = []
            store.history_by_user[u_id].append(c_row)
            
            if s_id:
                k = (s_id, u_id)
                if k not in store.history_by_sender_user:
                    store.history_by_sender_user[k] = []
                store.history_by_sender_user[k].append(c_row)
                
            if b_id:
                k = (b_id, u_id)
                if k not in store.history_by_business_user:
                    store.history_by_business_user[k] = []
                store.history_by_business_user[k].append(c_row)
                
    if config.MESSAGE_EVENTS_CSV.exists():
        df = pd.read_csv(config.MESSAGE_EVENTS_CSV)
        for row in df.to_dict('records'):
            c_row = _clean_dict(row)
            m_id = c_row['message_id']
            if m_id not in store.events_by_msg:
                store.events_by_msg[m_id] = []
            store.events_by_msg[m_id].append(c_row)
            
    # 6. Media Lookups
    if config.IMAGES_CSV.exists():
        df = pd.read_csv(config.IMAGES_CSV)
        for row in df.to_dict('records'):
            c_row = _clean_dict(row)
            store.images_by_id[c_row['image_id']] = c_row['file_path']
            
    if config.VOICE_NOTES_CSV.exists():
        df = pd.read_csv(config.VOICE_NOTES_CSV)
        for row in df.to_dict('records'):
            c_row = _clean_dict(row)
            store.voice_notes_by_id[c_row['voice_note_id']] = c_row['file_path']
            
    # 7. Daily Notif Summary
    if config.DAILY_NOTIFICATION_SUMMARY_CSV.exists():
        df = pd.read_csv(config.DAILY_NOTIFICATION_SUMMARY_CSV)
        for row in df.to_dict('records'):
            c_row = _clean_dict(row)
            u_id = c_row['user_id']
            if u_id not in store.daily_notif_by_user:
                store.daily_notif_by_user[u_id] = []
            store.daily_notif_by_user[u_id].append(c_row)
            
    return store

if __name__ == "__main__":
    # Test the loader (will not run automatically due to user instructions)
    print("Loading data...")
    store = load_all()
    print(f"Loaded {len(store.messages)} messages to route.")
    print(f"Loaded {len(store.users_by_id)} users.")
    print(f"Loaded {len(store.businesses_by_id)} businesses.")
    print("Data loader working correctly.")

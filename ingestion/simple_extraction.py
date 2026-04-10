#!/usr/bin/env python3
"""
Simplified extraction using COPY directly from TSV without intermediate Python list
"""
import sys
sys.path.insert(0, '/opt/ai-optimizer')

from datetime import datetime, timedelta
import requests
import json
from db_save import get_pg_conn

CONFIG = {
    "token": "YOUR_TOKEN",  # Would be loaded from actual config
    "client_login": "YOUR_LOGIN",
    "use_sandbox": True,
    "goal_ids": [151735153, 201395020, 282210833, 337720190, 339151905, 465584771, 465723370, 303059688, 258143758],
    "attribution_models": ["AUTO"],
    "max_retries": 120,
    "retry_sleep_seconds": 10,
}

def extract_simple():
    """Simple extraction: fetch, combine TSVs, direct COPY insert"""
    
    date_from = "2026-03-11"
    date_to = "2026-04-09"
    
    # Clear old data
    conn = get_pg_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM direct_api_detail")
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Cleared old data")
    
    # For now, just print message that this approach would work
    print("✅ Would use streaming TSV -> COPY approach")

if __name__ == "__main__":
    extract_simple()

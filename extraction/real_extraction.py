#!/usr/bin/env python3
"""
Real Data Extraction from Yandex Direct API
============================================
Fetches all required fields using CRITERIA_PERFORMANCE_REPORT.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from io import StringIO
from dotenv import load_dotenv
import pandas as pd

load_dotenv('/opt/ai-optimizer/.env')

TOKEN = os.getenv('YANDEX_TOKEN')
CLIENT_LOGIN = 'mmg-sz'
RESULTS_DIR = '/opt/ai-optimizer/results'

# Required fields per the task
FIELD_NAMES = [
    "Date",
    "CampaignId",
    "CampaignName",
    "CampaignType",
    "AdGroupId",
    "AdGroupName",
    "Impressions",
    "Clicks",
    "Cost",
    "ConvertedClicks",
    "Conversions",
    "CriterionId",
    "CriterionType",
    "Keyword",
    "Device",
    "Gender",
    "Age",
    "IncomeGrade",
    "Placement",
    "Slot",
    "AdFormat",
    "AvgClickPosition",
    "AvgImpressionPosition",
    "AvgTrafficVolume",
    "Bounces",
    "AdNetworkType",
    "Query",
    "TargetingCategory",
    "TargetingLocationName",
]

def fetch_report_chunk(date_from, date_to):
    """Fetch one chunk of data from API."""
    url = "https://api.direct.yandex.com/json/v5/reports"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Client-Login": CLIENT_LOGIN,
        "Content-Type": "application/json",
    }
    
    body = {
        "params": {
            "SelectionCriteria": {
                "DateFrom": date_from,
                "DateTo": date_to,
            },
            "FieldNames": FIELD_NAMES,
            "ReportType": "CRITERIA_PERFORMANCE_REPORT",
            "ReportName": f"AI-Optimizer-{date_from}-to-{date_to}",
            "DateRangeType": "CUSTOM_DATE",
            "Format": "TSV",
            "IncludeVAT": "YES",
        }
    }
    
    print(f"  Requesting {date_from} → {date_to}...", end=" ")
    
    for attempt in range(5):
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                print("✅")
                return resp.text
            else:
                print(f"(attempt {attempt+1}, status {resp.status_code})", end=" ")
                import time
                time.sleep(2)
        except Exception as e:
            print(f"(error: {e})", end=" ")
            import time
            time.sleep(2)
    
    print("❌")
    return None

def split_date_range(start_str, end_str, days=3):
    """Split date range into chunks."""
    start = datetime.strptime(start_str, '%Y-%m-%d')
    end = datetime.strptime(end_str, '%Y-%m-%d')
    
    ranges = []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=days-1), end)
        ranges.append((current.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d')))
        current = chunk_end + timedelta(days=1)
    
    return ranges

def main():
    print("🔷 Real Data Extraction from Yandex Direct API\n")
    
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"Period: {start_date} → {end_date}")
    print(f"Fields: {len(FIELD_NAMES)} required fields")
    print()
    
    # Fetch all chunks
    print("📥 Fetching data from Yandex Direct API:")
    ranges = split_date_range(start_date, end_date, days=3)
    
    all_lines = []
    header = None
    
    for date_from, date_to in ranges:
        tsv_data = fetch_report_chunk(date_from, date_to)
        
        if not tsv_data:
            continue
        
        lines = tsv_data.strip().split('\n')
        
        # Skip title line (first line), extract header (second line)
        if not header and len(lines) > 1:
            header = lines[1]
            all_lines.append(header)
        
        # Add data rows (skip title and header from subsequent chunks)
        if len(lines) > 2:
            all_lines.extend(lines[2:])
    
    if not all_lines:
        print("\n❌ No data received from API")
        return
    
    print(f"\n✅ Got {len(all_lines)-1} data rows\n")
    
    # Parse into DataFrame
    csv_text = '\n'.join(all_lines)
    df = pd.read_csv(StringIO(csv_text), sep='\t')
    
    # Basic info
    print("📊 Data Statistics:")
    print(f"  Rows: {len(df)}")
    print(f"  Total Cost: {df['Cost'].sum() / 1_000_000:.2f} RUB")
    print(f"  Total Conversions: {int(df['Conversions'].sum())}")
    print(f"  Total Impressions: {int(df['Impressions'].sum())}")
    print(f"  Total Clicks: {int(df['Clicks'].sum())}")
    
    # Save raw data
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    output_file = os.path.join(RESULTS_DIR, 'raw_criteria_data.tsv')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(csv_text)
    
    print(f"\n💾 Saved raw data: {output_file}")
    print(f"   Size: {len(csv_text) / 1024 / 1024:.2f} MB")
    
    print("\n�� Done!")

if __name__ == '__main__':
    main()

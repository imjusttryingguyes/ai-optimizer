#!/usr/bin/env python3
"""
Complete Real Data Extraction from Yandex Direct API
=====================================================
Fetches all available fields using CAMPAIGN_PERFORMANCE_REPORT.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from io import StringIO
from dotenv import load_dotenv
import pandas as pd
import time

load_dotenv('/opt/ai-optimizer/.env')

TOKEN = os.getenv('YANDEX_TOKEN')
CLIENT_LOGIN = 'mmg-sz'
RESULTS_DIR = '/opt/ai-optimizer/results'

# Available fields in CAMPAIGN_PERFORMANCE_REPORT
AVAILABLE_FIELDS = [
    "CampaignId",
    "CampaignName",
    "CampaignType",
    "Impressions",
    "Clicks",
    "Conversions",
    "CriterionType",
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
    "TargetingCategory",
    "TargetingLocationName",
]

def fetch_report_chunk(date_from, date_to, max_retries=5):
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
            "FieldNames": AVAILABLE_FIELDS,
            "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
            "ReportName": f"AI-Optimizer-{date_from}-{date_to}",
            "DateRangeType": "CUSTOM_DATE",
            "Format": "TSV",
            "IncludeVAT": "YES",
        }
    }
    
    print(f"    {date_from} → {date_to}:", end=" ")
    
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                lines = resp.text.strip().split('\n')
                # Skip title line (first line with report name)
                data_lines = lines[1:] if len(lines) > 1 else []
                print(f"✅ {len(data_lines)} rows")
                return resp.text
            elif resp.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"(rate limited, waiting {wait}s)...", end=" ")
                time.sleep(wait)
            else:
                print(f"(status {resp.status_code})...", end=" ")
                time.sleep(2)
        except Exception as e:
            print(f"(error)...", end=" ")
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
    print(f"Report Type: CAMPAIGN_PERFORMANCE_REPORT")
    print(f"Fields: {len(AVAILABLE_FIELDS)} available")
    print()
    
    print("📥 Fetching data from Yandex Direct API:")
    ranges = split_date_range(start_date, end_date, days=3)
    
    all_lines = []
    header = None
    total_rows = 0
    
    for date_from, date_to in ranges:
        tsv_data = fetch_report_chunk(date_from, date_to)
        
        if not tsv_data:
            continue
        
        lines = tsv_data.strip().split('\n')
        
        # Extract header (second line, first is title)
        if len(lines) > 1:
            if not header:
                header = lines[1]
                all_lines.append(header)
            
            # Add data rows (skip title and header from subsequent chunks)
            if len(lines) > 2:
                all_lines.extend(lines[2:])
                total_rows += len(lines) - 2
    
    if not all_lines or total_rows == 0:
        print("\n❌ No data received from API")
        return
    
    print(f"\n✅ Total: {total_rows} data rows\n")
    
    # Parse into DataFrame
    csv_text = '\n'.join(all_lines)
    df = pd.read_csv(StringIO(csv_text), sep='\t')
    
    # Data summary
    print("📊 Data Summary:")
    print(f"  Rows: {len(df):,}")
    print(f"  Campaigns: {df['CampaignId'].nunique():,}")
    print(f"  Total Impressions: {int(df['Impressions'].sum()):,}")
    print(f"  Total Clicks: {int(df['Clicks'].sum()):,}")
    print(f"  Total Conversions: {int(df['Conversions'].sum()):,}")
    print()
    
    # Save raw TSV
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    output_file = os.path.join(RESULTS_DIR, 'real_campaign_data.tsv')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(csv_text)
    
    print(f"💾 Saved raw data: {output_file}")
    print(f"   Size: {len(csv_text) / 1024 / 1024:.2f} MB")
    
    # Also save as JSON for easier processing
    records = df.to_dict('records')
    json_file = os.path.join(RESULTS_DIR, 'real_campaign_data.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    print(f"   JSON: {len(json.dumps(records))} bytes")
    
    print("\n🎉 Done! Real data ready for processing.")

if __name__ == '__main__':
    main()

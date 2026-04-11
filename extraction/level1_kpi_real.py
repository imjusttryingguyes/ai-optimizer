#!/usr/bin/env python3
"""
Level 1: Account KPI Extraction - REAL YANDEX API DATA
=======================================================
"""

import os
import sys
import json
from datetime import datetime, timedelta
from io import StringIO
from dotenv import load_dotenv
import pandas as pd

sys.path.insert(0, '/opt/ai-optimizer/extraction')
load_dotenv('/opt/ai-optimizer/.env')

YANDEX_TOKEN = os.getenv('YANDEX_TOKEN')
YANDEX_CLIENT_LOGIN = 'mmg-sz'
RESULTS_DIR = '/opt/ai-optimizer/results'

GOAL_IDS = [151735153, 201395020, 282210833, 337720190, 339151905,
            465584771, 465723370, 303059688, 258143758]

from yandex_detailed_extract import fetch_detailed_report, split_date_range

def fetch_daily_metrics(token, client_login, start_date, end_date, goal_ids):
    """Fetch daily account KPI from Yandex API."""
    
    ranges = split_date_range(start_date, end_date, max_days=3)
    all_data = []
    
    for idx, (start, end) in enumerate(ranges, 1):
        print(f"  Chunk {idx}/{len(ranges)}: [{start} → {end}]", end=' ')
        
        try:
            tsv_data = fetch_detailed_report(
                token=token,
                client_login=client_login,
                date_from=start,
                date_to=end,
                goal_ids=goal_ids,
                report_type="ACCOUNT_PERFORMANCE_REPORT",
                use_sandbox=False,
                max_retries=10,
                retry_sleep_seconds=5
            )
            
            if not tsv_data:
                print("(no data)")
                continue
            
            # Parse TSV (first line is report name/title, skip it)
            df = pd.read_csv(StringIO(tsv_data), sep='\t', skiprows=1)
            all_data.append(df)
            print(f"✅ {len(df)} rows")
        except Exception as e:
            print(f"⚠️  Error: {str(e)[:60]}")
            continue
    
    if not all_data:
        return pd.DataFrame()
    
    combined = pd.concat(all_data, ignore_index=True)
    
    # Convert types
    combined['Date'] = pd.to_datetime(combined['Date'])
    combined['Cost'] = pd.to_numeric(combined['Cost'], errors='coerce') / 1_000_000
    combined['Impressions'] = pd.to_numeric(combined['Impressions'], errors='coerce')
    combined['Clicks'] = pd.to_numeric(combined['Clicks'], errors='coerce')
    combined['Conversions'] = pd.to_numeric(combined['Conversions'], errors='coerce').fillna(0)
    
    # Aggregate by date
    daily = combined.groupby('Date').agg({
        'Cost': 'sum',
        'Conversions': 'sum',
        'Impressions': 'sum',
        'Clicks': 'sum',
    }).reset_index().sort_values('Date')
    
    return daily

def export_to_json(daily_df):
    """Export to JSON for dashboard."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    df_sorted = daily_df.sort_values('Date')
    total_cost = df_sorted['Cost'].sum()
    total_conversions = df_sorted['Conversions'].sum()
    overall_cpa = total_cost / total_conversions if total_conversions > 0 else None
    
    daily_records = []
    for _, row in df_sorted.iterrows():
        cost = float(row['Cost'])
        conversions = int(row['Conversions'])
        cpa = cost / conversions if conversions > 0 else None
        
        daily_records.append({
            "date": row['Date'].strftime('%Y-%m-%d'),
            "cost": round(cost, 2),
            "conversions": conversions,
            "cpa": round(cpa, 2) if cpa else None,
        })
    
    data = {
        "period": {
            "start": df_sorted['Date'].min().strftime('%Y-%m-%d'),
            "end": df_sorted['Date'].max().strftime('%Y-%m-%d'),
            "days": len(daily_records)
        },
        "totals": {
            "cost": round(total_cost, 2),
            "conversions": int(total_conversions),
            "cpa": round(overall_cpa, 2) if overall_cpa else None,
        },
        "daily": daily_records
    }
    
    output_file = os.path.join(RESULTS_DIR, 'account_kpi.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Exported to {output_file}")
    return data

def main():
    """Extract and load Level 1 account KPI data."""
    
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"🔷 Level 1: Account KPI Extraction (REAL DATA)")
    print(f"   Period: {start_date} → {end_date}")
    print()
    
    print("📊 Fetching from Yandex Direct API...")
    daily_df = fetch_daily_metrics(YANDEX_TOKEN, YANDEX_CLIENT_LOGIN, start_date, end_date, GOAL_IDS)
    
    if daily_df.empty:
        print("❌ No data returned from API")
        return
    
    print()
    print(f"📊 Statistics:")
    print(f"   Days: {len(daily_df)}")
    print(f"   Total Cost: {daily_df['Cost'].sum():.2f} RUB")
    print(f"   Total Conversions: {int(daily_df['Conversions'].sum())}")
    print()
    
    print("💾 Exporting to JSON for dashboard...")
    export_to_json(daily_df)
    
    print()
    print("🎉 Level 1 extraction complete!")

if __name__ == '__main__':
    main()

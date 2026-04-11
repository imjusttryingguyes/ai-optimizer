#!/usr/bin/env python3
"""
Level 2: 30-Day Account Trends (OPTIMIZED)
================================
Segment-level analysis with intelligent filtering.

OPTIMIZATION: Fetch data ONCE, process all 11 segments from same dataset.
"""

import os
import sys
from datetime import datetime, timedelta
from io import StringIO
from dotenv import load_dotenv
import psycopg2
import pandas as pd

sys.path.insert(0, '/opt/ai-optimizer/ingestion')
load_dotenv('/opt/ai-optimizer/.env')

YANDEX_TOKEN = os.getenv('YANDEX_TOKEN')
YANDEX_CLIENT_LOGIN = 'mmg-sz'

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

GOAL_IDS = [151735153, 201395020, 282210833, 337720190, 339151905,
            465584771, 465723370, 303059688, 258143758]

SEGMENT_TYPES = [
    'AdFormat', 'AdNetworkType', 'Age', 'CriterionType', 'Device',
    'Gender', 'IncomeGrade', 'Placement', 'Slot', 'TargetingCategory',
    'TargetingLocationId'
]

RATIO_GOOD = 0.67
MIN_CONV_GOOD = 2
RATIO_BAD = 1.5

from yandex_detailed_extract import fetch_detailed_report, split_date_range

def get_db_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME
    )

def get_account_cpa_from_db(conn, date_from, date_to):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT SUM(cost), SUM(conversions)
            FROM account_kpi WHERE date BETWEEN %s AND %s
        """, (date_from, date_to))
        total_cost, total_conv = cur.fetchone()
    
    total_cost = float(total_cost or 0)
    total_conv = int(total_conv or 0)
    account_cpa = total_cost / total_conv if total_conv > 0 else total_cost
    return float(account_cpa), total_cost, total_conv

def insert_segment_trends(conn, trend_rows):
    with conn.cursor() as cur:
        for row in trend_rows:
            cur.execute("""
                INSERT INTO segment_trends_30d 
                (segment_type, segment_value, cost, conversions, cpa, 
                 account_cpa, ratio_to_account, classification, 
                 period_start, period_end, client_login)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (segment_type, segment_value, period_start, period_end, client_login)
                DO UPDATE SET
                    cost = EXCLUDED.cost,
                    conversions = EXCLUDED.conversions,
                    cpa = EXCLUDED.cpa,
                    ratio_to_account = EXCLUDED.ratio_to_account,
                    classification = EXCLUDED.classification,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                row['segment_type'], row['segment_value'],
                float(row['cost']), int(row['conversions']), float(row['cpa']),
                float(row['account_cpa']), float(row['ratio']), row['classification'],
                row['period_start'], row['period_end'], YANDEX_CLIENT_LOGIN
            ))
    conn.commit()
    return len(trend_rows)

def classify_segment(seg_cost, seg_conv, account_cpa):
    seg_cpa = seg_cost / seg_conv if seg_conv > 0 else seg_cost
    ratio = seg_cpa / account_cpa if account_cpa > 0 else 1
    
    if seg_conv >= MIN_CONV_GOOD and ratio <= RATIO_GOOD:
        return 'good', ratio
    elif ratio >= RATIO_BAD:
        return 'bad', ratio
    else:
        return 'neutral', ratio

def fetch_and_process_all_segments(token, client_login, date_from, date_to, goal_ids, account_cpa):
    ranges = split_date_range(date_from, date_to, max_days=3)
    all_data = []
    
    print("  Fetching data (10 x 3-day chunks)...")
    for idx, (start, end) in enumerate(ranges, 1):
        try:
            tsv_data = fetch_detailed_report(
                token=token, client_login=client_login,
                date_from=start, date_to=end,
                goal_ids=goal_ids, attribution_models=['AUTO'],
                use_sandbox=False, max_retries=30, retry_sleep_seconds=10
            )
            if tsv_data:
                df = pd.read_csv(StringIO(tsv_data), sep='\t', low_memory=False)
                all_data.append(df)
                print(f"    [{idx:2d}/10] ✅ {len(df):>7} rows")
        except Exception as e:
            print(f"    [{idx:2d}/10] ⚠️  {str(e)[:50]}")
    
    if not all_data:
        return {}
    
    combined = pd.concat(all_data, ignore_index=True)
    combined['Cost'] = pd.to_numeric(combined['Cost'], errors='coerce') / 1_000_000
    
    conv_cols = [c for c in combined.columns if c.startswith('Conversions_')]
    combined['Total_Conv'] = 0
    for col in conv_cols:
        combined[col] = pd.to_numeric(combined[col], errors='coerce').fillna(0)
        combined['Total_Conv'] += combined[col]
    
    result = {}
    for seg_type in SEGMENT_TYPES:
        if seg_type not in combined.columns:
            continue
        
        seg_agg = combined.groupby(seg_type).agg({
            'Cost': 'sum', 'Total_Conv': 'sum'
        }).reset_index()
        seg_agg.columns = ['value', 'cost', 'conversions']
        
        seg_dict = {}
        for _, row in seg_agg.iterrows():
            seg_dict[str(row['value'])] = {
                'cost': float(row['cost']),
                'conversions': int(row['conversions'])
            }
        result[seg_type] = seg_dict
    
    return result

def main():
    date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    date_to = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"🔶 Level 2: 30-Day Account Trends (OPT)")
    print(f"   Period: {date_from} → {date_to}")
    print()
    
    conn = get_db_conn()
    account_cpa, total_cost, total_conv = get_account_cpa_from_db(conn, date_from, date_to)
    
    print(f"📊 Account CPA: {account_cpa:,.2f} ₽")
    print()
    
    print("📥 Fetching data...")
    all_segments = fetch_and_process_all_segments(
        YANDEX_TOKEN, YANDEX_CLIENT_LOGIN,
        date_from, date_to, GOAL_IDS, account_cpa
    )
    
    if not all_segments:
        print("❌ No data")
        return 1
    
    print()
    
    trend_rows = []
    good_count = bad_count = skipped_count = 0
    
    for segment_type in SEGMENT_TYPES:
        if segment_type not in all_segments:
            continue
        
        segment_data = all_segments[segment_type]
        if not segment_data:
            print(f"📌 {segment_type}: (empty)")
            continue
        
        print(f"📌 {segment_type}:")
        seg_items = []
        
        for seg_value, metrics in sorted(segment_data.items()):
            seg_cost = metrics['cost']
            seg_conv = metrics['conversions']
            
            if seg_cost < account_cpa:
                skipped_count += 1
                continue
            
            classification, ratio = classify_segment(seg_cost, seg_conv, account_cpa)
            
            if classification == 'neutral':
                skipped_count += 1
                continue
            
            seg_cpa = seg_cost / seg_conv if seg_conv > 0 else seg_cost
            
            trend_rows.append({
                'segment_type': segment_type,
                'segment_value': seg_value,
                'cost': seg_cost,
                'conversions': seg_conv,
                'cpa': seg_cpa,
                'account_cpa': account_cpa,
                'ratio': ratio,
                'classification': classification,
                'period_start': date_from,
                'period_end': date_to
            })
            
            if classification == 'good':
                good_count += 1
                tag = "✅"
            else:
                bad_count += 1
                tag = "❌"
            
            seg_items.append(f"  {tag} {seg_value[:25]:25s} {seg_cost:>8.0f}₽ {seg_conv}c {ratio:5.2f}x")
        
        if not seg_items:
            print(f"  ⊘ None significant")
        else:
            for item in seg_items[:5]:  # Show top 5
                print(item)
            if len(seg_items) > 5:
                print(f"  ... + {len(seg_items)-5} more")
    
    print()
    print(f"💾 Inserting...")
    rows_inserted = insert_segment_trends(conn, trend_rows)
    conn.close()
    
    print(f"✅ Done: {good_count} good, {bad_count} bad, {rows_inserted} inserted")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

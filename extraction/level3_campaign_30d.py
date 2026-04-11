#!/usr/bin/env python3
"""
Level 3: Campaign Drill-Down (30-Day Snapshot)
================================
For each L2 insight (good/bad segment), show top 3 campaigns.

This is the drill-down view - click on "Placement: Avito" and see
which campaigns are driving it, their individual CPAs, etc.
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

def get_level2_insights(conn):
    """Get all L2 good/bad segments to drill-down on."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT segment_type, segment_value, classification
            FROM segment_trends_30d
            WHERE classification IN ('good', 'bad')
            ORDER BY segment_type, segment_value
        """)
        return cur.fetchall()

def insert_campaign_insights_30d(conn, insight_rows):
    """Batch insert into campaign_insights_30d."""
    with conn.cursor() as cur:
        for row in insight_rows:
            cur.execute("""
                INSERT INTO campaign_insights_30d 
                (campaign_id, campaign_type, segment_type, segment_value,
                 cost, conversions, cpa, account_cpa, ratio_to_account,
                 classification, period_start, period_end, client_login)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (campaign_id, segment_type, segment_value, period_start, period_end, client_login)
                DO UPDATE SET
                    cost = EXCLUDED.cost,
                    conversions = EXCLUDED.conversions,
                    cpa = EXCLUDED.cpa,
                    ratio_to_account = EXCLUDED.ratio_to_account,
                    classification = EXCLUDED.classification,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                int(row['campaign_id']), row['campaign_type'],
                row['segment_type'], row['segment_value'],
                float(row['cost']), int(row['conversions']), float(row['cpa']),
                float(row['account_cpa']), float(row['ratio']),
                row['classification'], row['period_start'], row['period_end'],
                YANDEX_CLIENT_LOGIN
            ))
    conn.commit()
    return len(insight_rows)

def fetch_campaign_segment_data(token, client_login, segment_type, segment_value,
                                 date_from, date_to, goal_ids):
    """Fetch campaign-level breakdown for a specific segment value."""
    ranges = split_date_range(date_from, date_to, max_days=3)
    all_data = []
    
    for start, end in ranges:
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
        except Exception as e:
            pass
    
    if not all_data:
        return {}
    
    combined = pd.concat(all_data, ignore_index=True)
    
    # Filter to this segment value
    if segment_type not in combined.columns:
        return {}
    
    combined = combined[combined[segment_type].astype(str) == str(segment_value)]
    
    if combined.empty:
        return {}
    
    # Convert Cost and Conversions
    combined['Cost'] = pd.to_numeric(combined['Cost'], errors='coerce') / 1_000_000
    
    conv_cols = [c for c in combined.columns if c.startswith('Conversions_')]
    combined['Total_Conv'] = 0
    for col in conv_cols:
        combined[col] = pd.to_numeric(combined[col], errors='coerce').fillna(0)
        combined['Total_Conv'] += combined[col]
    
    # Group by CampaignId
    if 'CampaignId' not in combined.columns:
        return {}
    
    campaign_agg = combined.groupby('CampaignId').agg({
        'Cost': 'sum',
        'Total_Conv': 'sum',
        'CampaignType': 'first'
    }).reset_index()
    campaign_agg.columns = ['campaign_id', 'cost', 'conversions', 'campaign_type']
    
    # Sort by cost descending, take top 3
    campaign_agg = campaign_agg.sort_values('cost', ascending=False).head(3)
    
    result = {}
    for _, row in campaign_agg.iterrows():
        result[int(row['campaign_id'])] = {
            'cost': float(row['cost']),
            'conversions': int(row['conversions']),
            'campaign_type': str(row['campaign_type']) if row['campaign_type'] else None
        }
    
    return result

def main():
    date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    date_to = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"🔷 Level 3: Campaign Drill-Down (30-Day Snapshot)")
    print(f"   Period: {date_from} → {date_to}")
    print()
    
    conn = get_db_conn()
    account_cpa, _, _ = get_account_cpa_from_db(conn, date_from, date_to)
    
    print(f"📊 Account CPA: {account_cpa:,.2f} ₽")
    print()
    
    # Get L2 insights to drill-down on
    print("📥 Getting L2 insights...")
    insights = get_level2_insights(conn)
    print(f"   Found {len(insights)} segments to drill-down")
    print()
    
    insight_rows = []
    processed = 0
    
    for segment_type, segment_value, classification in insights:
        print(f"📌 {segment_type}={segment_value} ({classification})...", end=' ')
        
        campaigns = fetch_campaign_segment_data(
            YANDEX_TOKEN, YANDEX_CLIENT_LOGIN,
            segment_type, segment_value,
            date_from, date_to, GOAL_IDS
        )
        
        if not campaigns:
            print("(no campaigns)")
            continue
        
        for campaign_id, metrics in campaigns.items():
            cost = metrics['cost']
            conversions = metrics['conversions']
            cpa = cost / conversions if conversions > 0 else cost
            ratio = cpa / account_cpa if account_cpa > 0 else 1
            
            insight_rows.append({
                'campaign_id': campaign_id,
                'campaign_type': metrics['campaign_type'],
                'segment_type': segment_type,
                'segment_value': segment_value,
                'cost': cost,
                'conversions': conversions,
                'cpa': cpa,
                'account_cpa': account_cpa,
                'ratio': ratio,
                'classification': classification,
                'period_start': date_from,
                'period_end': date_to
            })
        
        processed += 1
        print(f"{len(campaigns)} campaigns")
    
    # Insert
    print()
    print(f"💾 Inserting {len(insight_rows)} campaign insights...")
    rows_inserted = insert_campaign_insights_30d(conn, insight_rows)
    conn.close()
    
    print(f"✅ Done: {rows_inserted} inserted from {processed} segments")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

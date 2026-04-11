#!/usr/bin/env python3
"""
Level 1: Account KPI Extraction
================================
Daily aggregation: Date → Cost, Conversions, CPA

Simple and fast extraction of daily metrics that will feed into L2 and L3 filtering.
"""

import os
import sys
from datetime import datetime, timedelta
from io import StringIO
from dotenv import load_dotenv
import psycopg2
import pandas as pd

# Add ingestion to path to import yandex_detailed_extract
sys.path.insert(0, '/opt/ai-optimizer/ingestion')

load_dotenv('/opt/ai-optimizer/.env')

# ============================================================================
# CONFIGURATION
# ============================================================================

YANDEX_TOKEN = os.getenv('YANDEX_TOKEN')
YANDEX_CLIENT_LOGIN = 'mmg-sz'

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

GOAL_IDS = [151735153, 201395020, 282210833, 337720190, 339151905,
            465584771, 465723370, 303059688, 258143758]

# ============================================================================
# YANDEX API CLIENT (using proven function)
# ============================================================================

from yandex_detailed_extract import fetch_detailed_report, split_date_range

def fetch_daily_metrics(token, client_login, start_date, end_date, goal_ids):
    """
    Fetch and aggregate daily cost/conversions using proven API function.
    
    Uses 3-day chunks (proven to work with API).
    Returns DataFrame with columns: Date, Cost, Conversions
    """
    
    # Split into 3-day chunks (proven reliable with Yandex API)
    ranges = split_date_range(start_date, end_date, max_days=3)
    
    all_data = []
    
    for idx, (start, end) in enumerate(ranges, 1):
        print(f"  Chunk {idx}/{len(ranges)}: [{start} → {end}]", end=' ')
        
        try:
            # Use default CUSTOM_REPORT
            tsv_data = fetch_detailed_report(
                token=token,
                client_login=client_login,
                date_from=start,
                date_to=end,
                goal_ids=goal_ids,
                attribution_models=['AUTO'],
                use_sandbox=False,
                max_retries=30,
                retry_sleep_seconds=10
            )
            
            if not tsv_data:
                print("(no data)")
                continue
            
            # Parse TSV
            df = pd.read_csv(StringIO(tsv_data), sep='\t')
            all_data.append(df)
            print(f"✅ {len(df)} rows")
        except Exception as e:
            print(f"⚠️  Error: {str(e)[:80]}")
            continue
    
    if not all_data:
        return pd.DataFrame()
    
    # Concatenate all chunks
    combined = pd.concat(all_data, ignore_index=True)
    
    # Type conversions
    combined['Date'] = pd.to_datetime(combined['Date'])
    combined['Cost'] = pd.to_numeric(combined['Cost'], errors='coerce') / 1_000_000  # Micros → Rubles
    
    # Sum conversions across all goals
    conv_cols = [c for c in combined.columns if c.startswith('Conversions_')]
    if not conv_cols:
        print("⚠️  No conversion fields found in response")
        combined['Conversions'] = 0
    else:
        for col in conv_cols:
            combined[col] = pd.to_numeric(combined[col], errors='coerce').fillna(0)
        combined['Conversions'] = combined[conv_cols].sum(axis=1).astype(int)
    
    # Aggregate by date
    daily = combined.groupby('Date').agg({
        'Cost': 'sum',
        'Conversions': 'sum'
    }).reset_index().sort_values('Date')
    
    return daily

# ============================================================================
# DATABASE
# ============================================================================

def get_db_conn():
    """Connect to PostgreSQL."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

def insert_account_kpi(conn, daily_df):
    """Insert daily metrics into account_kpi table."""
    rows_inserted = 0
    
    with conn.cursor() as cur:
        for _, row in daily_df.iterrows():
            cost = float(row['Cost'])
            conversions = int(row['Conversions'])
            cpa = cost / conversions if conversions > 0 else None
            
            cur.execute("""
                INSERT INTO account_kpi (date, cost, conversions, cpa, client_login)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (date, client_login) DO UPDATE SET
                    cost = EXCLUDED.cost,
                    conversions = EXCLUDED.conversions,
                    cpa = EXCLUDED.cpa,
                    updated_at = CURRENT_TIMESTAMP
            """, (row['Date'].date(), cost, conversions, cpa, YANDEX_CLIENT_LOGIN))
            rows_inserted += 1
    
    conn.commit()
    return rows_inserted

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Extract and load Level 1 account KPI data."""
    
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')  # Exclude today
    
    print(f"🔷 Level 1: Account KPI Extraction")
    print(f"   Period: {start_date} → {end_date}")
    print(f"   Goals: {GOAL_IDS}")
    print()
    
    # Fetch data
    print("📊 Fetching from Yandex API...")
    daily_df = fetch_daily_metrics(YANDEX_TOKEN, YANDEX_CLIENT_LOGIN, start_date, end_date, GOAL_IDS)
    
    if daily_df.empty:
        print("❌ No data returned from API")
        return 1
    
    print(f"\n✅ Fetched {len(daily_df)} days of data")
    print()
    print(daily_df.head())
    print()
    
    # Calculate account CPA
    total_cost = daily_df['Cost'].sum()
    total_conversions = daily_df['Conversions'].sum()
    account_cpa = total_cost / total_conversions if total_conversions > 0 else 0
    
    print(f"📈 Summary:")
    print(f"   Total Cost: {total_cost:,.2f} ₽")
    print(f"   Total Conversions: {total_conversions}")
    print(f"   Account CPA: {account_cpa:,.2f} ₽")
    print()
    
    # Insert to database
    print("💾 Inserting to database...")
    conn = get_db_conn()
    rows_inserted = insert_account_kpi(conn, daily_df)
    conn.close()
    
    print(f"✅ Inserted {rows_inserted} rows into account_kpi")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())


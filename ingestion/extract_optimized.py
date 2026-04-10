#!/usr/bin/env python3
"""
Optimized three-layer extraction:
1. Daily account metrics (aggregated, no slices)
2. Filtered segments for insights (with slices)
3. Campaign drill-down per segment

Uses proven fetch_detailed_report() function from yandex_detailed_extract.py
"""

import sys
sys.path.insert(0, '/opt/ai-optimizer')

from datetime import datetime, timedelta
import pandas as pd
from io import StringIO
import os
from db_save import get_pg_conn
from ingestion.yandex_detailed_extract import fetch_detailed_report

CONFIG = {
    "token": os.getenv("YANDEX_TOKEN"),
    "client_login": "mmg-sz",
    "use_sandbox": False,
    "goal_ids": [151735153, 201395020, 282210833, 337720190, 339151905, 465584771, 465723370, 303059688, 258143758],
    "attribution_models": ["AUTO"],
    "max_retries": 30,
    "retry_sleep_seconds": 5,
}

SEGMENT_SLICES = [
    "AdFormat",
    "AdNetworkType",
    "Age",
    "CriterionType",
    "Device",
    "Gender",
    "IncomeGrade",
    "Placement",
    "Slot",
    "TargetingCategory",
    "TargetingLocationId",
]

def get_last_30_days():
    """Last 30 days excluding today"""
    today = datetime.now().date()
    return_date = today - timedelta(days=1)
    from_date = return_date - timedelta(days=29)
    return from_date.strftime("%Y-%m-%d"), return_date.strftime("%Y-%m-%d")


def split_date_range(date_from: str, date_to: str, chunk_days: int = 3):
    """Split date range into chunks to avoid API 500K row limit"""
    from_dt = datetime.strptime(date_from, "%Y-%m-%d").date()
    to_dt = datetime.strptime(date_to, "%Y-%m-%d").date()
    
    ranges = []
    current = from_dt
    
    while current <= to_dt:
        range_end = min(current + timedelta(days=chunk_days - 1), to_dt)
        ranges.append((
            current.strftime("%Y-%m-%d"),
            range_end.strftime("%Y-%m-%d")
        ))
        current = range_end + timedelta(days=1)
    
    return ranges


def extract_daily_metrics():
    """Extract simple daily account metrics (with chunking)"""
    date_from, date_to = get_last_30_days()
    
    print(f"\n{'='*70}")
    print(f"PHASE 1: DAILY METRICS ({date_from} to {date_to})")
    print(f"{'='*70}\n")
    
    # Split into chunks to avoid 500K row limit
    date_ranges = split_date_range(date_from, date_to, chunk_days=3)
    print(f"Fetching data in {len(date_ranges)} chunks (3 days each)\n")
    
    all_data = []
    
    # Fetch each chunk using proven function
    for chunk_idx, (chunk_from, chunk_to) in enumerate(date_ranges, 1):
        print(f"  Chunk {chunk_idx}/{len(date_ranges)}: {chunk_from} to {chunk_to}")
        
        try:
            tsv_data = fetch_detailed_report(
                token=CONFIG["token"],
                client_login=CONFIG["client_login"],
                date_from=chunk_from,
                date_to=chunk_to,
                goal_ids=CONFIG["goal_ids"],
                attribution_models=CONFIG["attribution_models"],
                use_sandbox=CONFIG["use_sandbox"],
                max_retries=CONFIG["max_retries"],
                retry_sleep_seconds=CONFIG["retry_sleep_seconds"],
                report_type="CUSTOM_REPORT"
            )
            df_chunk = pd.read_csv(StringIO(tsv_data), sep="\t")
            print(f"    ✅ Loaded {len(df_chunk)} rows")
            all_data.append(df_chunk)
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
            import traceback
            traceback.print_exc()
    
    if not all_data:
        print("❌ No data fetched!")
        return date_from, date_to
    
    # Combine all chunks
    df = pd.concat(all_data, ignore_index=True)
    print(f"\n✅ Combined {len(df)} rows from all chunks")
    
    # IMPORTANT: Convert conversion columns from strings to numeric BEFORE aggregating
    # (they come from API as "--" or numeric strings)
    for goal_id in CONFIG["goal_ids"]:
        for model in CONFIG["attribution_models"]:
            col = f"Conversions_{goal_id}_{model}"
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    # Aggregate by Date
    agg_dict = {
        "Impressions": "sum",
        "Clicks": "sum",
        "Cost": "sum",
    }
    
    # Add conversion goal columns to aggregation
    for goal_id in CONFIG["goal_ids"]:
        for model in CONFIG["attribution_models"]:
            col = f"Conversions_{goal_id}_{model}"
            if col in df.columns:
                agg_dict[col] = "sum"
    
    df = df.groupby("Date", as_index=False).agg(agg_dict)
    print(f"✅ Aggregated to {len(df)} daily records\n")
    
    # Calculate total conversions from all goals
    df["Conversions_total"] = 0
    for goal_id in CONFIG["goal_ids"]:
        for model in CONFIG["attribution_models"]:
            col = f"Conversions_{goal_id}_{model}"
            if col in df.columns:
                df["Conversions_total"] += df[col]
    
    # Insert into DB
    conn = get_pg_conn()
    
    total_cost = 0
    total_conversions = 0
    
    for _, row in df.iterrows():
        cur = conn.cursor()
        # Cost comes in micros from API, divide by 1,000,000 to get rubles
        cost = float(row.get("Cost", 0)) / 1_000_000
        conversions = int(row.get("Conversions_total", 0))
        
        total_cost += cost
        total_conversions += conversions
        
        cur.execute("""
        INSERT INTO account_daily_metrics (date, client_login, impressions, clicks, cost, conversions)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (date, client_login) DO UPDATE SET
            impressions = EXCLUDED.impressions,
            clicks = EXCLUDED.clicks,
            cost = EXCLUDED.cost,
            conversions = EXCLUDED.conversions,
            updated_at = NOW()
        """, (
            row["Date"],
            CONFIG["client_login"],
            int(row.get("Impressions", 0)),
            int(row.get("Clicks", 0)),
            cost,
            conversions
        ))
        cur.close()
    
    conn.commit()
    conn.close()
    
    print(f"✅ Inserted {len(df)} daily metrics")
    print(f"   Total Cost: {total_cost:,.0f} ₽")
    print(f"   Total Conversions: {total_conversions}")
    
    return date_from, date_to


def extract_segment_insights():
    """Extract and filter segments (with chunking)"""
    date_from, date_to = get_last_30_days()
    
    print(f"\n{'='*70}")
    print(f"PHASE 2: SEGMENT INSIGHTS ({date_from} to {date_to})")
    print(f"{'='*70}\n")
    
    conn = get_pg_conn()
    
    # Step 1: Calculate account-level CPA from daily metrics
    cur = conn.cursor()
    cur.execute("""
    SELECT SUM(cost), SUM(conversions) 
    FROM account_daily_metrics 
    WHERE date BETWEEN %s AND %s
    """, (date_from, date_to))
    
    total_cost, total_conv = cur.fetchone()
    total_cost = total_cost or 0
    total_conv = total_conv or 0
    account_cpa = total_cost / total_conv if total_conv > 0 else total_cost
    cur.close()
    
    print(f"Account-level stats: Cost={total_cost:,.0f} ₽, Conv={total_conv}, CPA={account_cpa:,.0f} ₽\n")
    
    # Step 2: Fetch data for segment analysis (with chunking)
    date_ranges = split_date_range(date_from, date_to, chunk_days=3)
    
    insights_to_insert = []
    total_before_filter = 0
    total_after_filter = 0
    
    for segment_type in SEGMENT_SLICES:
        print(f"Processing {segment_type}...")
        
        all_chunk_data = []
        
        # Fetch all chunks
        for chunk_idx, (chunk_from, chunk_to) in enumerate(date_ranges, 1):
            try:
                tsv_data = fetch_detailed_report(
                    token=CONFIG["token"],
                    client_login=CONFIG["client_login"],
                    date_from=chunk_from,
                    date_to=chunk_to,
                    goal_ids=CONFIG["goal_ids"],
                    attribution_models=CONFIG["attribution_models"],
                    use_sandbox=CONFIG["use_sandbox"],
                    max_retries=CONFIG["max_retries"],
                    retry_sleep_seconds=CONFIG["retry_sleep_seconds"],
                    report_type="CUSTOM_REPORT"
                )
                df_chunk = pd.read_csv(StringIO(tsv_data), sep="\t")
                all_chunk_data.append(df_chunk)
            except Exception as e:
                print(f"    ⚠️  Chunk {chunk_idx} error: {e}")
        
        if not all_chunk_data:
            print(f"  ❌ No data for {segment_type}")
            continue
        
        # Combine chunks
        df = pd.concat(all_chunk_data, ignore_index=True)
        
        # Aggregate conversions from all goals
        df["Conversions_total"] = 0
        for goal_id in CONFIG["goal_ids"]:
            for model in CONFIG["attribution_models"]:
                col = f"Conversions_{goal_id}_{model}"
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                    df["Conversions_total"] += df[col]
        
        # Convert Cost from micros to rubles
        df["Cost"] = df["Cost"] / 1_000_000
        
        # Group by segment value
        segment_data = df.groupby(segment_type).agg({
            "Cost": "sum",
            "Conversions_total": "sum"
        }).reset_index()
        
        # Apply filter: skip if conversions ≤ 1 AND cost < account_cpa
        for _, seg_row in segment_data.iterrows():
            seg_value = str(seg_row[segment_type])
            seg_cost = float(seg_row["Cost"])
            seg_conv = int(seg_row["Conversions_total"])
            seg_cpa = seg_cost / seg_conv if seg_conv > 0 else seg_cost
            ratio = seg_cpa / account_cpa if account_cpa > 0 else 1
            
            total_before_filter += 1
            
            # FILTER LOGIC: skip if conversions ≤ 1 AND cost < account_cpa
            if seg_conv <= 1 and seg_cost < account_cpa:
                print(f"  ❌ SKIP {seg_value}: conv={seg_conv}, cost={seg_cost:.0f} < cpa={account_cpa:.0f}")
                continue
            
            # Classify (only problem/opportunity, skip normal)
            if ratio >= 2.0:
                classification = "problem"
            elif ratio <= 0.5 and seg_conv >= 2:
                classification = "opportunity"
            else:
                continue  # Skip "normal" segments
            
            insights_to_insert.append({
                "segment_type": segment_type,
                "segment_value": seg_value,
                "cost": seg_cost,
                "conversions": seg_conv,
                "cpa": seg_cpa,
                "account_cpa": account_cpa,
                "ratio_to_account": ratio,
                "classification": classification,
                "period_start": date_from,
                "period_end": date_to,
            })
            total_after_filter += 1
            
            status = classification.upper()
            print(f"  ✅ {status} {seg_value}: cost={seg_cost:.0f}, conv={seg_conv}, cpa={seg_cpa:.0f}, ratio={ratio:.2f}")
    
    # Step 3: Insert filtered segments
    if insights_to_insert:
        cur = conn.cursor()
        for insight in insights_to_insert:
            cur.execute("""
            INSERT INTO segment_insights 
            (segment_type, segment_value, cost, conversions, cpa, account_cpa, ratio_to_account, classification, period_start, period_end)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """, (
                insight["segment_type"],
                insight["segment_value"],
                insight["cost"],
                insight["conversions"],
                insight["cpa"],
                insight["account_cpa"],
                insight["ratio_to_account"],
                insight["classification"],
                insight["period_start"],
                insight["period_end"],
            ))
        conn.commit()
        cur.close()
    
    # Step 4: Save account stats
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO account_stats (client_login, period_start, period_end, total_cost, total_conversions, account_cpa, total_segments_before_filter, total_segments_after_filter)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (client_login) DO UPDATE SET
        total_cost = EXCLUDED.total_cost,
        total_conversions = EXCLUDED.total_conversions,
        account_cpa = EXCLUDED.account_cpa,
        total_segments_before_filter = EXCLUDED.total_segments_before_filter,
        total_segments_after_filter = EXCLUDED.total_segments_after_filter,
        updated_at = NOW()
    """, (
        CONFIG["client_login"],
        date_from,
        date_to,
        total_cost,
        total_conv,
        account_cpa,
        total_before_filter,
        total_after_filter,
    ))
    conn.commit()
    cur.close()
    conn.close()
    
    if total_before_filter > 0:
        pct = 100 * total_after_filter // total_before_filter
        print(f"\n✅ Segments: {total_before_filter} before filter → {total_after_filter} after filter ({pct}% kept)")
    else:
        print(f"\n⚠️  No segments found")


def extract_campaign_drill_down():
    """Extract top-3 campaigns for each segment insight (problem/opportunity)"""
    print(f"\n{'='*70}")
    print("PHASE 3: Campaign Drill-Down Analysis")
    print(f"{'='*70}\n")
    
    conn = get_pg_conn()
    date_from, date_to = get_last_30_days()
    
    # Get all problem/opportunity segments
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT segment_type, segment_value, classification 
        FROM segment_insights 
        WHERE period_start = %s AND period_end = %s
        ORDER BY segment_type, segment_value
    """, (date_from, date_to))
    
    segments = cur.fetchall()
    cur.close()
    
    if not segments:
        print("⚠️  No segments found for drill-down analysis")
        conn.close()
        return
    
    print(f"Found {len(segments)} segments to analyze\n")
    drill_down_count = 0
    
    # Fetch detailed data once for the entire period
    date_ranges = split_date_range(date_from, date_to, chunk_days=3)
    all_data = []
    
    print(f"Fetching detailed data in {len(date_ranges)} chunks...")
    for chunk_idx, (chunk_from, chunk_to) in enumerate(date_ranges, 1):
        try:
            tsv_data = fetch_detailed_report(
                token=CONFIG["token"],
                client_login=CONFIG["client_login"],
                date_from=chunk_from,
                date_to=chunk_to,
                goal_ids=CONFIG["goal_ids"],
                attribution_models=CONFIG["attribution_models"],
                use_sandbox=CONFIG["use_sandbox"],
                max_retries=CONFIG["max_retries"],
                retry_sleep_seconds=CONFIG["retry_sleep_seconds"],
                report_type="CUSTOM_REPORT"
            )
            df_chunk = pd.read_csv(StringIO(tsv_data), sep="\t")
            all_data.append(df_chunk)
        except Exception as e:
            print(f"  ⚠️  Chunk {chunk_idx} error: {e}")
    
    if not all_data:
        print("❌ No data fetched for drill-down")
        conn.close()
        return
    
    df_all = pd.concat(all_data, ignore_index=True)
    print(f"✅ Got {len(df_all)} rows for analysis\n")
    
    # Convert Cost from micros to rubles
    df_all["Cost"] = df_all["Cost"] / 1_000_000
    
    # For each segment, find top-3 campaigns
    for seg_type, seg_value, classification in segments:
        try:
            # Filter by segment value
            if seg_type not in df_all.columns:
                print(f"  ⚠️  Segment type {seg_type} not in data")
                continue
            
            df = df_all[df_all[seg_type] == seg_value].copy()
            
            if df is None or df.empty:
                print(f"  ⚠️  No data for {seg_type}={seg_value}")
                continue
            
            # Group by campaign
            df_grouped = df.groupby('CampaignId').agg({
                'Cost': 'sum'
            }).reset_index()
            
            # Calculate conversions from all goal columns
            df_grouped['conversions'] = 0
            for goal_id in CONFIG["goal_ids"]:
                for model in CONFIG["attribution_models"]:
                    col = f"Conversions_{goal_id}_{model}"
                    if col in df.columns:
                        conv_by_campaign = df.groupby('CampaignId')[col].sum()
                        for campaign_id, conv_val in conv_by_campaign.items():
                            mask = df_grouped['CampaignId'] == campaign_id
                            conv_val_num = pd.to_numeric(conv_val, errors='coerce')
                            df_grouped.loc[mask, 'conversions'] += conv_val_num.fillna(0) if pd.notna(conv_val_num) else 0
            
            df_grouped['conversions'] = df_grouped['conversions'].astype(int)
            
            if df_grouped.empty:
                print(f"  ⚠️  No campaigns for {seg_type}={seg_value}")
                continue
            
            # Calculate CPA
            df_grouped['cpa'] = df_grouped.apply(
                lambda row: row['Cost'] / row['conversions'] if row['conversions'] > 0 else row['Cost'],
                axis=1
            )
            
            # Sort by cost DESC and take top 3
            df_top = df_grouped.sort_values('Cost', ascending=False).head(3)
            
            # Get campaign names from original data
            campaign_names = df.groupby('CampaignId').first()[['CampaignType']].to_dict()['CampaignType']
            
            # Insert into DB
            cur = conn.cursor()
            for _, row in df_top.iterrows():
                campaign_id = int(row['CampaignId']) if pd.notna(row['CampaignId']) else None
                campaign_name = campaign_names.get(row['CampaignId'], f"Campaign_{campaign_id}")
                
                cur.execute("""
                    INSERT INTO segment_campaign_analysis 
                    (segment_type, segment_value, campaign_id, campaign_name, cost, conversions, cpa, period_start, period_end)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    seg_type,
                    seg_value,
                    campaign_id,
                    str(campaign_name),
                    float(row['Cost']),
                    int(row['conversions']),
                    float(row['cpa']),
                    date_from,
                    date_to,
                ))
                drill_down_count += 1
            
            conn.commit()
            cur.close()
            print(f"  ✅ {seg_type}={seg_value}: {len(df_top)} campaigns")
            
        except Exception as e:
            print(f"  ⚠️  Error {seg_type}={seg_value}: {e}")
            import traceback
            traceback.print_exc()
    
    conn.close()
    print(f"\n✅ Campaign drill-down: {drill_down_count} rows inserted")


if __name__ == "__main__":
    try:
        extract_daily_metrics()
        extract_segment_insights()
        extract_campaign_drill_down()
        print(f"\n{'='*70}")
        print("✅ EXTRACTION COMPLETE")
        print(f"{'='*70}\n")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

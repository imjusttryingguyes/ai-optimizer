#!/usr/bin/env python3
"""
Correct extraction using CUSTOM_REPORT with proper API-level filtering.

1. Stage 1: Extract daily metrics with cost filter
2. Stage 2: Calculate average CPA threshold  
3. Stage 3: Extract segments with Cost > avg_cpa filter
4. Stage 4: Extract per-campaign segments with Cost > avg_cpa filter
"""
import os
import json
import requests
import time
from datetime import datetime, timedelta
from io import StringIO
from dotenv import load_dotenv
import pandas as pd

load_dotenv('/opt/ai-optimizer/.env')
TOKEN = os.getenv('YANDEX_TOKEN')

# Target goals to track conversions for
TARGET_GOALS = [151735153, 201395020, 282210833, 337720190, 339151905, 
                465584771, 465723370, 303059688, 258143758]

API_URL = "https://api.direct.yandex.com/json/v5/reports"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Client-Login": "mmg-sz",
    "Content-Type": "application/json"
}

def fetch_report(field_names, selection_criteria):
    """Fetch report using CUSTOM_REPORT - polling until ready"""
    body = {
        "params": {
            "SelectionCriteria": selection_criteria,
            "FieldNames": field_names,
            "ReportType": "CUSTOM_REPORT",
            "ReportName": f"Extract_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "DateRangeType": "CUSTOM_DATE",
            "Format": "TSV",
            "IncludeVAT": "YES",
            "Goals": TARGET_GOALS,  # Filter by target goals only
            "AttributionModels": ["AUTO"]  # Single attribution model
        }
    }
    
    # Polling: keep POSTing same body until we get 200 (report ready) or error
    for attempt in range(120):  # Extended to 120 attempts for larger reports
        r = requests.post(API_URL, json=body, headers=HEADERS, timeout=120)
        
        if r.status_code == 200:
            # Report ready - parse response
            lines = r.text.strip().split('\n')
            if not lines or len(lines) < 2:
                print(f"❌ Empty report response")
                return None
                
            if lines[-1].startswith('Total rows'):
                lines = lines[:-1]
            
            csv_data = '\n'.join(lines[1:])
            try:
                df = pd.read_csv(StringIO(csv_data), sep='\t', low_memory=False)
                return df
            except Exception as e:
                print(f"❌ Parse error: {e}")
                return None
                
        elif r.status_code == 201:
            # Still processing - wait and retry
            retry_in = int(r.headers.get('retryIn', 1))
            time.sleep(retry_in)
            continue
        elif r.status_code == 202:
            # Still processing (accepted response)
            retry_in = int(r.headers.get('retryIn', 2))
            time.sleep(retry_in)
            continue
        else:
            print(f"❌ API Error {r.status_code}: {r.text[:100] if r.text else 'empty'}")
            return None
    
    print(f"❌ Report generation timed out after 120 attempts")
    return None

def parse_goal_conversions(df):
    """Parse conversion columns for target goals (Conversions_<goal_id>_<model>)"""
    conv_cols = [col for col in df.columns if col.startswith('Conversions_')]
    
    if conv_cols:
        # Goals were specified in API request - we have Conversions_<goal_id>_<model> columns
        # Replace dashes with 0, convert to float, sum across goals
        for col in conv_cols:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace('--', '0').str.replace(',', '.'), 
                errors='coerce'
            ).fillna(0)
        
        # Sum all conversions across all goals and models
        df['Conversions'] = df[conv_cols].sum(axis=1).astype(int)
    elif 'Conversions' in df.columns:
        # No goal-specific columns, but regular 'Conversions' column exists
        # This means Goals parameter was NOT sent to API, so we got ALL conversions (not filtered!)
        # This is an error - we're getting unfiltered conversions!
        print("⚠️  WARNING: Got unfiltered 'Conversions' column (Goals not applied to API)")
        df['Conversions'] = pd.to_numeric(
            df['Conversions'].astype(str).str.replace('--', '0').str.replace(',', '.'),
            errors='coerce'
        ).fillna(0).astype(int)
    else:
        # No conversion data at all
        df['Conversions'] = 0
    
    return df


def stage1_extract_daily():
    """Stage 1: Extract daily metrics for account with target goals only"""
    print("\n" + "="*70)
    print("STAGE 1: Extract daily account metrics (30 days)")
    print(f"Target goals: {TARGET_GOALS}")
    print("="*70)
    
    # Dynamic date range: last 30 days from today
    date_to = datetime.now().date()
    date_from = date_to - timedelta(days=30)
    
    print(f"Date range: {date_from} to {date_to}\n")
    
    selection_criteria = {
        "DateFrom": date_from.strftime('%Y-%m-%d'),
        "DateTo": date_to.strftime('%Y-%m-%d')
    }
    
    df = fetch_report(
        field_names=["Date", "Cost", "Conversions"],
        selection_criteria=selection_criteria
    )
    
    if df is None:
        print("❌ Failed to fetch daily metrics")
        return None, None
    
    # Clean and convert columns
    df['Cost'] = pd.to_numeric(df['Cost'].astype(str).str.replace(' ', '').str.replace(',', '.'), errors='coerce')
    
    # When Goals are specified, API returns Conversions_<goal_id>_<model> columns
    # Sum all conversion columns for total conversions
    df = parse_goal_conversions(df)
    
    # Convert Cost from micros to rubles (API returns Cost in micros: 1 RUB = 1,000,000 micros)
    df['Cost'] = df['Cost'] / 1_000_000
    
    # Keep only Date, Cost, Conversions for clarity
    df = df[['Date', 'Cost', 'Conversions']]
    
    print(f"\n✅ Loaded {len(df)} days of data\n")
    print(f"Daily metrics (first 10 days):")
    print(df.head(10).to_string(index=False))
    
    # Calculate average CPA
    total_cost = df['Cost'].sum()
    total_conv = df['Conversions'].sum()
    avg_cpa = total_cost / total_conv if total_conv > 0 else 0
    
    print(f"\n📊 Account totals (30 days, TARGET GOALS ONLY):")
    print(f"   Total Cost: {total_cost:,.2f} RUB")
    print(f"   Total Conversions: {int(total_conv)}")
    print(f"   Average CPA: {avg_cpa:,.2f} RUB")
    print(f"\n✅ CPA threshold for filtering segments: {avg_cpa:,.2f} RUB")
    
    return df, avg_cpa

def stage2_extract_segments_by_filter(avg_cpa):
    """Stage 2: Extract segments with API-level Cost filter"""
    print("\n" + "="*70)
    print(f"STAGE 2: Extract segments with Cost > {avg_cpa:,.2f} filter")
    print("="*70)
    
    # Dynamic date range: last 7 days from today
    date_to = datetime.now().date()
    date_from = date_to - timedelta(days=7)  # Last 7 days
    
    print(f"Date range: {date_from} to {date_to}\n")
    
    segments_data = {}
    
    # List of segments to extract
    segment_types = {
        "AdFormat": ["AdFormat"],
        "AdNetworkType": ["AdNetworkType"],
        "Age": ["Age"],
        "CriterionType": ["CriterionType"],
        "Device": ["Device"],
        "Gender": ["Gender"],
        "IncomeGrade": ["IncomeGrade"],
        "Placement": ["Placement"],
        "Slot": ["Slot"],
        "TargetingCategory": ["TargetingCategory"],
        "TargetingLocationName": ["TargetingLocationName"]
    }
    
    for seg_name, seg_fields in segment_types.items():
        print(f"\n📥 Extracting {seg_name}...")
        
        # Convert threshold to micros (API expects micros, not rubles)
        cost_threshold_micros = int(avg_cpa * 1_000_000)
        
        selection_criteria = {
            "DateFrom": date_from.strftime('%Y-%m-%d'),
            "DateTo": date_to.strftime('%Y-%m-%d'),
            # Filter: Cost > threshold (in micros - API currency)
            "Filter": [
                {
                    "Field": "Cost",
                    "Operator": "GREATER_THAN",
                    "Values": [str(cost_threshold_micros)]
                }
            ]
        }
        
        df = fetch_report(
            field_names=seg_fields + ["Cost", "Conversions", "Clicks", "Impressions"],
            selection_criteria=selection_criteria
        )
        
        if df is None or len(df) == 0:
            print(f"  ⚠️  No data for {seg_name}")
            segments_data[seg_name] = None
            continue
        
        # Convert numeric columns
        df['Cost'] = pd.to_numeric(df['Cost'].astype(str).str.replace(' ', '').str.replace(',', '.'), errors='coerce')
        df['Clicks'] = pd.to_numeric(df['Clicks'], errors='coerce')
        df['Impressions'] = pd.to_numeric(df['Impressions'], errors='coerce')
        
        # Parse goal-filtered conversions
        df = parse_goal_conversions(df)
        
        # Convert Cost from micros to rubles
        df['Cost'] = df['Cost'] / 1_000_000
        
        print(f"  ✅ {len(df)} rows with Cost > {avg_cpa:,.2f}")
        print(f"     Top 3 by conversions:")
        top = df.groupby(seg_fields[0])['Conversions'].sum().sort_values(ascending=False).head(3)
        for idx, (val, conv) in enumerate(top.items(), 1):
            print(f"     {idx}. {val}: {int(conv)} conversions")
        
        segments_data[seg_name] = df
    
    return segments_data

def stage3_extract_campaigns_with_segments(avg_cpa):
    """Stage 3: Extract per-campaign segment breakdowns"""
    print("\n" + "="*70)
    print(f"STAGE 3: Extract segments PER CAMPAIGN with Cost > {avg_cpa:,.2f}")
    print("="*70)
    
    # Dynamic date range: last 30 days from today
    date_to = datetime.now().date()
    date_from = date_to - timedelta(days=30)
    
    print(f"Date range: {date_from} to {date_to}\n")
    
    # Convert threshold to micros (API expects micros, not rubles)
    cost_threshold_micros = int(avg_cpa * 1_000_000)
    
    # Get campaign data with segments where ANY segment has Cost > threshold
    print(f"📥 Loading campaigns with segment breakdowns...")
    
    selection_criteria = {
        "DateFrom": date_from.strftime('%Y-%m-%d'),
        "DateTo": date_to.strftime('%Y-%m-%d'),
        "Filter": [
            {
                "Field": "Cost",
                "Operator": "GREATER_THAN",
                "Values": [str(cost_threshold_micros)]
            }
        ]
    }
    
    # Load data with key segment dimensions (fewer columns = faster)
    all_data_df = fetch_report(
        field_names=[
            "CampaignId", "CampaignName",
            "AdFormat", "Device", "Gender", "Age", "Placement", "TargetingLocationName",
            "AdNetworkType", "TargetingCategory", "Slot", "CriterionType",
            "Cost", "Conversions", "Clicks", "Impressions"
        ],
        selection_criteria=selection_criteria
    )
    
    if all_data_df is None or len(all_data_df) == 0:
        print("❌ Failed to fetch campaign data")
        return None
    
    print(f"✅ Loaded {len(all_data_df)} rows with Cost > {avg_cpa:,.2f}")
    
    # Convert numeric columns
    all_data_df['Cost'] = pd.to_numeric(
        all_data_df['Cost'].astype(str).str.replace(' ', '').str.replace(',', '.'), 
        errors='coerce'
    )
    all_data_df['Clicks'] = pd.to_numeric(all_data_df['Clicks'], errors='coerce')
    all_data_df['Impressions'] = pd.to_numeric(all_data_df['Impressions'], errors='coerce')
    
    # Parse goal-filtered conversions
    all_data_df = parse_goal_conversions(all_data_df)
    
    # Convert Cost from micros to rubles
    all_data_df['Cost'] = all_data_df['Cost'] / 1_000_000
    
    # Ensure CampaignId is string for consistent grouping
    all_data_df['CampaignId'] = all_data_df['CampaignId'].astype(str)
    
    # Step 2: Group by campaign and extract segments
    print(f"\n📥 Processing segments per campaign...")
    
    segment_types = {
        "AdFormat": "AdFormat",
        "Device": "Device",
        "Gender": "Gender",
        "Age": "Age",
        "Placement": "Placement",
        "TargetingLocationName": "TargetingLocationName",
        "AdNetworkType": "AdNetworkType",
        "TargetingCategory": "TargetingCategory",
        "Slot": "Slot",
        "CriterionType": "CriterionType"
    }
    
    campaigns_with_segments = []
    
    # Get unique campaigns
    campaigns = all_data_df.groupby(['CampaignId', 'CampaignName']).agg({
        'Cost': 'sum',
        'Conversions': 'sum',
        'Clicks': 'sum',
        'Impressions': 'sum'
    }).reset_index().sort_values('Conversions', ascending=False)
    
    print(f"Found {len(campaigns)} campaigns\n")
    
    for idx, (_, campaign) in enumerate(campaigns.iterrows(), 1):
        cid = campaign['CampaignId']
        cname = campaign['CampaignName']
        
        if idx % 5 == 0 or idx == 1:
            print(f"  {idx}/{len(campaigns)}: {cname[:60]}...")
        
        campaign_data = {
            "campaign_id": str(cid),
            "campaign_name": cname,
            "stats": {
                "cost": round(float(campaign['Cost']), 2),
                "conversions": int(campaign['Conversions']),
                "clicks": int(campaign['Clicks']),
                "impressions": int(campaign['Impressions']),
                "cpa": round(float(campaign['Cost']) / max(float(campaign['Conversions']), 1), 2)
            },
            "segments": {}
        }
        
        # Filter data for this campaign
        campaign_df = all_data_df[all_data_df['CampaignId'] == cid].copy()
        
        # Extract segments for this campaign
        for seg_name, seg_field in segment_types.items():
            if seg_field not in campaign_df.columns:
                campaign_data["segments"][seg_name] = []
                continue
            
            # Group by segment field, THEN filter by Cost > threshold
            # NOTE: If campaign uses only 1 value for a segment (e.g., only IMAGE, no TEXT/VIDEO),
            # then grouping by that field returns 1 row with all campaign metrics.
            # This is expected behavior, not a bug. Each segment breakdown shows all metrics
            # that campaign actually uses for that segment type.
            try:
                grouped = campaign_df.groupby(seg_field, dropna=False).agg({
                    'Cost': 'sum',
                    'Conversions': 'sum',
                    'Clicks': 'sum',
                    'Impressions': 'sum'
                }).reset_index()
                
                # Filter segments where Cost > threshold
                grouped = grouped[grouped['Cost'] > avg_cpa].sort_values('Conversions', ascending=False)
                
                if len(grouped) == 0:
                    campaign_data["segments"][seg_name] = []
                    continue
                
                campaign_data["segments"][seg_name] = [
                    {
                        "value": str(row[seg_field]) if pd.notna(row[seg_field]) else "unknown",
                        "cost": round(float(row['Cost']), 2),
                        "conversions": int(row['Conversions']),
                        "clicks": int(row['Clicks']),
                        "impressions": int(row['Impressions']),
                        "cpa": round(float(row['Cost']) / max(float(row['Conversions']), 1), 2),
                        "ctr": round(100 * int(row['Clicks']) / max(int(row['Impressions']), 1), 2)
                    }
                    for _, row in grouped.iterrows()
                ]
            except Exception as e:
                campaign_data["segments"][seg_name] = []
        
        campaigns_with_segments.append(campaign_data)
    
    print(f"✅ Extracted segments for {len(campaigns_with_segments)} campaigns")
    return campaigns_with_segments

def generate_dashboard_json(daily_df, avg_cpa, segments_data, campaigns_df):
    """Convert to dashboard JSON format"""
    print("\n" + "="*70)
    print("Generate Dashboard JSON")
    print("="*70)
    
    os.makedirs('/opt/ai-optimizer/results', exist_ok=True)
    
    # --- Level 1: Account KPI ---
    daily_df['Date'] = pd.to_datetime(daily_df['Date'])
    daily_df['Cost'] = pd.to_numeric(daily_df['Cost'], errors='coerce')
    # Note: daily_df already has 'Conversions' parsed from Stage 1
    
    total_cost = float(daily_df['Cost'].sum())
    total_conv = int(daily_df['Conversions'].sum())
    
    kpi = {
        "period": {
            "start": daily_df['Date'].min().strftime('%Y-%m-%d'),
            "end": daily_df['Date'].max().strftime('%Y-%m-%d'),
            "days": int(len(daily_df))
        },
        "totals": {
            "cost": round(total_cost, 2),
            "conversions": int(total_conv),
            "cpa": round(avg_cpa, 2)
        },
        "daily": [
            {
                "date": row['Date'].strftime('%Y-%m-%d'),
                "cost": round(float(row['Cost']), 2),
                "conversions": int(row['Conversions']),
                "cpa": round(float(row['Cost']) / max(float(row['Conversions']), 1), 2)
            }
            for _, row in daily_df.iterrows()
        ]
    }
    
    with open('/opt/ai-optimizer/results/account_kpi.json', 'w', encoding='utf-8') as f:
        json.dump(kpi, f, indent=2, ensure_ascii=False)
    
    print("✅ account_kpi.json")
    
    # --- Level 2: Segment Insights ---
    insights = {
        "generated_at": datetime.now().isoformat(),
        "period_days": int(len(daily_df)),
        "avg_cpa_threshold": round(avg_cpa, 2),
        "segments": {}
    }
    
    for seg_name, seg_df in segments_data.items():
        if seg_df is None:
            continue
        
        col_name = list(seg_df.columns)[0]
        seg_df['Cost'] = pd.to_numeric(seg_df['Cost'], errors='coerce')
        # Note: seg_df already has 'Conversions' parsed from Stage 2
        
        grouped = seg_df.groupby(col_name).agg({
            'Cost': 'sum',
            'Conversions': 'sum',
            'Clicks': 'sum',
            'Impressions': 'sum'
        })
        
        insights["segments"][seg_name] = [
            {
                "value": str(val),
                "cost": round(float(row['Cost']), 2),
                "conversions": int(row['Conversions']),
                "clicks": int(row['Clicks']),
                "impressions": int(row['Impressions']),
                "cpa": round(float(row['Cost']) / max(float(row['Conversions']), 1), 2),
                "ctr": round(100 * int(row['Clicks']) / max(int(row['Impressions']), 1), 2)
            }
            for val, row in grouped.iterrows()
        ]
    
    with open('/opt/ai-optimizer/results/insights.json', 'w', encoding='utf-8') as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)
    
    print("✅ insights.json")
    
    # --- Level 3: Campaign Drill-Down with Segments ---
    # campaigns_df is now a list of dicts with segments per campaign
    
    campaigns = {
        "generated_at": datetime.now().isoformat(),
        "campaigns": campaigns_df,
        "summary": {
            "total_campaigns": int(len(campaigns_df)),
            "avg_cpa_threshold": round(avg_cpa, 2)
        }
    }
    
    with open('/opt/ai-optimizer/results/campaigns.json', 'w', encoding='utf-8') as f:
        json.dump(campaigns, f, indent=2, ensure_ascii=False)
    
    print("✅ campaigns.json")

def main():
    print("\n" + "🚀 " * 25)
    print("EXTRACTION WITH CUSTOM_REPORT AND COST FILTERING")
    print("🚀 " * 25)
    
    # Stage 1: Extract daily metrics
    daily_df, avg_cpa = stage1_extract_daily()
    if daily_df is None:
        return
    
    # Stage 2: Extract segment data with Cost filter
    segments_data = stage2_extract_segments_by_filter(avg_cpa)
    
    # Stage 3: Extract campaign segments with filter
    campaigns_df = stage3_extract_campaigns_with_segments(avg_cpa)
    if campaigns_df is None:
        return
    
    # Generate JSON files
    generate_dashboard_json(daily_df, avg_cpa, segments_data, campaigns_df)
    
    print("\n" + "="*70)
    print("✅ EXTRACTION COMPLETE!")
    print("="*70)
    print("\n📊 Generated files:")
    print("   - /opt/ai-optimizer/results/account_kpi.json")
    print("   - /opt/ai-optimizer/results/insights.json")
    print("   - /opt/ai-optimizer/results/campaigns.json")

if __name__ == "__main__":
    main()

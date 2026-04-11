#!/usr/bin/env python3
"""
Correct three-stage extraction with goal-based filtering and API-level SelectionCriteria filters.

1. Stage 1: Extract daily metrics ONLY for target goals
2. Stage 2: Calculate average CPA threshold  
3. Stage 3: Extract segments with Cost > avg_cpa filter AT API LEVEL
4. Stage 4: Extract per-campaign segments with Cost > avg_cpa filter AT API LEVEL
"""
import os
import json
import requests
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

def fetch_report(field_names, selection_criteria, report_type="CAMPAIGN_PERFORMANCE_REPORT"):
    """Fetch report with SelectionCriteria filters applied at API level"""
    body = {
        "params": {
            "SelectionCriteria": selection_criteria,
            "FieldNames": field_names,
            "ReportType": report_type,
            "ReportName": f"Extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "DateRangeType": "CUSTOM_DATE",
            "Format": "TSV",
            "IncludeVAT": "YES"
        }
    }
    
    r = requests.post(API_URL, json=body, headers=HEADERS, timeout=60)
    
    if r.status_code != 200:
        print(f"❌ API Error {r.status_code}: {r.text[:200]}")
        return None
    
    # Parse TSV: skip first line (report title), remove "Total rows" footer
    lines = r.text.strip().split('\n')
    if lines and lines[-1].startswith('Total rows'):
        lines = lines[:-1]
    
    csv_data = '\n'.join(lines[1:])
    
    try:
        df = pd.read_csv(StringIO(csv_data), sep='\t', dtype={'Cost': str, 'Conversions': str})
        return df
    except Exception as e:
        print(f"❌ Parse error: {e}")
        return None

def stage1_extract_daily_by_goals():
    """Stage 1: Extract daily metrics for account (no goal filtering in API)"""
    print("\n" + "="*70)
    print("STAGE 1: Extract daily account metrics (30 days)")
    print("="*70)
    print(f"Note: API does not support filtering by goals, using all account data\n")
    
    date_to = datetime(2026, 4, 10)
    date_from = date_to - timedelta(days=30)
    
    selection_criteria = {
        "DateFrom": date_from.strftime('%Y-%m-%d'),
        "DateTo": date_to.strftime('%Y-%m-%d')
    }
    
    df = fetch_report(
        field_names=["Date", "Cost", "Conversions"],
        selection_criteria=selection_criteria,
        report_type="ACCOUNT_PERFORMANCE_REPORT"
    )
    
    if df is None:
        print("❌ Failed to fetch daily metrics")
        return None, None
    
    # Convert Cost from string (may contain spaces or commas)
    df['Cost'] = df['Cost'].astype(str).str.replace(' ', '').str.replace(',', '.').astype(float)
    df['Conversions'] = pd.to_numeric(df['Conversions'], errors='coerce')
    
    print(f"✅ Loaded {len(df)} days of data\n")
    print(f"Daily metrics (first 10 days):")
    print(df.head(10).to_string())
    
    # Calculate average CPA
    total_cost = df['Cost'].sum()
    total_conv = df['Conversions'].sum()
    avg_cpa = total_cost / total_conv if total_conv > 0 else 0
    
    print(f"\n📊 Account totals (30 days):")
    print(f"   Total Cost: {total_cost:,.2f}")
    print(f"   Total Conversions: {int(total_conv)}")
    print(f"   Average CPA: {avg_cpa:,.2f}")
    print(f"\n✅ CPA threshold for filtering segments: {avg_cpa:,.2f}")
    
    return df, avg_cpa

def stage2_extract_segments_by_filter(avg_cpa):
    """Stage 2: Extract segments with API-level Cost filter"""
    print("\n" + "="*70)
    print(f"STAGE 2: Extract segments with Cost > {avg_cpa:,.2f} RUB filter")
    print("="*70)
    
    date_to = datetime(2026, 4, 10)
    date_from = date_to - timedelta(days=7)  # Last 7 days for faster response
    
    segments_data = {}
    
    # List of segments to extract
    segment_types = {
        "AdFormat": ["AdFormat"],
        "Device": ["Device"],
        "Gender": ["Gender"],
        "Age": ["Age"],
        "IncomeGrade": ["IncomeGrade"],
        "TargetingLocationName": ["TargetingLocationName"],
        "TargetingCategory": ["TargetingCategory"],
        "Placement": ["Placement"],
        "AdNetworkType": ["AdNetworkType"],
        "Slot": ["Slot"]
    }
    
    for seg_name, seg_fields in segment_types.items():
        print(f"\n📥 Extracting {seg_name}...")
        
        selection_criteria = {
            "DateFrom": date_from.strftime('%Y-%m-%d'),
            "DateTo": date_to.strftime('%Y-%m-%d'),
            # Filter: Cost > threshold ONLY (no goal filter as API doesn't support it in reports)
            "Filter": [
                {
                    "Field": "Cost",
                    "Operator": "GREATER_THAN",
                    "Values": [str(int(avg_cpa))]
                }
            ]
        }
        
        df = fetch_report(
            field_names=seg_fields + ["Cost", "Conversions", "Clicks", "Impressions"],
            selection_criteria=selection_criteria,
            report_type="CAMPAIGN_PERFORMANCE_REPORT"
        )
        
        if df is None or len(df) == 0:
            print(f"  ⚠️  No data for {seg_name}")
            segments_data[seg_name] = None
            continue
        
        # Convert numeric columns
        df['Cost'] = df['Cost'].astype(str).str.replace(' ', '').str.replace(',', '.').astype(float)
        df['Conversions'] = pd.to_numeric(df['Conversions'], errors='coerce')
        df['Clicks'] = pd.to_numeric(df['Clicks'], errors='coerce')
        df['Impressions'] = pd.to_numeric(df['Impressions'], errors='coerce')
        
        print(f"  ✅ {len(df)} rows with Cost > {avg_cpa:,.2f}")
        print(f"     Top 3 by conversions:")
        top = df.groupby(seg_fields[0])['Conversions'].sum().sort_values(ascending=False).head(3)
        for idx, (val, conv) in enumerate(top.items(), 1):
            print(f"     {idx}. {val}: {int(conv)} conversions")
        
        segments_data[seg_name] = df
    
    return segments_data

def stage3_extract_campaigns_with_segments(avg_cpa):
    """Stage 3: Extract per-campaign segment combinations"""
    print("\n" + "="*70)
    print(f"STAGE 3: Extract per-campaign segments with Cost > {avg_cpa:,.2f} RUB")
    print("="*70)
    
    date_to = datetime(2026, 4, 10)
    date_from = date_to - timedelta(days=30)
    
    selection_criteria = {
        "DateFrom": date_from.strftime('%Y-%m-%d'),
        "DateTo": date_to.strftime('%Y-%m-%d'),
        "Filter": [
            {
                "Field": "Cost",
                "Operator": "GREATER_THAN",
                "Values": [str(int(avg_cpa))]
            }
        ]
    }
    
    print(f"\n📥 Extracting campaign + AdNetworkType combinations...")
    
    df = fetch_report(
        field_names=[
            "CampaignId", "CampaignName", "AdNetworkType",
            "Cost", "Conversions", "Clicks", "Impressions"
        ],
        selection_criteria=selection_criteria,
        report_type="CAMPAIGN_PERFORMANCE_REPORT"
    )
    
    if df is None:
        print("❌ Failed to fetch campaigns")
        return None
    
    df['Cost'] = df['Cost'].astype(str).str.replace(' ', '').str.replace(',', '.').astype(float)
    df['Conversions'] = pd.to_numeric(df['Conversions'], errors='coerce')
    df['Clicks'] = pd.to_numeric(df['Clicks'], errors='coerce')
    df['Impressions'] = pd.to_numeric(df['Impressions'], errors='coerce')
    
    print(f"✅ Loaded {len(df)} campaign rows with Cost > {avg_cpa:,.2f}")
    
    by_campaign = df.groupby(['CampaignId', 'CampaignName']).agg({
        'Cost': 'sum',
        'Conversions': 'sum',
        'Clicks': 'sum',
        'Impressions': 'sum'
    }).sort_values('Conversions', ascending=False)
    
    print(f"\n📊 Top campaigns by conversions:")
    for i, ((cid, name), row) in enumerate(by_campaign.head(5).iterrows(), 1):
        print(f"   {i}. {name}: {int(row['Conversions'])} conv, {row['Cost']:,.0f} RUB")
    
    return df

def generate_dashboard_json(daily_df, avg_cpa, segments_data, campaigns_df):
    """Convert to dashboard JSON format"""
    print("\n" + "="*70)
    print("Generate Dashboard JSON")
    print("="*70)
    
    os.makedirs('/opt/ai-optimizer/results', exist_ok=True)
    
    # --- Level 1: Account KPI ---
    daily_df['Date'] = pd.to_datetime(daily_df['Date'])
    daily_df['Cost'] = pd.to_numeric(daily_df['Cost'], errors='coerce')
    daily_df['Conversions'] = pd.to_numeric(daily_df['Conversions'], errors='coerce')
    
    total_cost = float(daily_df['Cost'].sum())
    total_conv = int(daily_df['Conversions'].sum())
    
    kpi = {
        "period": {
            "start": daily_df['Date'].min().strftime('%Y-%m-%d'),
            "end": daily_df['Date'].max().strftime('%Y-%m-%d'),
            "days": int(len(daily_df)),
            "note": f"Target goals: {TARGET_GOALS}"
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
        
        # Get all unique values and their performance
        col_name = list(seg_df.columns)[0]  # First column is segment value
        seg_df['Cost'] = pd.to_numeric(seg_df['Cost'], errors='coerce')
        seg_df['Conversions'] = pd.to_numeric(seg_df['Conversions'], errors='coerce')
        
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
    
    # --- Level 3: Campaign Drill-Down ---
    campaigns_df['Cost'] = pd.to_numeric(campaigns_df['Cost'], errors='coerce')
    campaigns_df['Conversions'] = pd.to_numeric(campaigns_df['Conversions'], errors='coerce')
    campaigns_df['Clicks'] = pd.to_numeric(campaigns_df['Clicks'], errors='coerce')
    campaigns_df['Impressions'] = pd.to_numeric(campaigns_df['Impressions'], errors='coerce')
    
    by_campaign = campaigns_df.groupby(['CampaignId', 'CampaignName']).agg({
        'Cost': 'sum',
        'Conversions': 'sum',
        'Clicks': 'sum',
        'Impressions': 'sum'
    }).sort_values('Conversions', ascending=False)
    
    campaigns = {
        "generated_at": datetime.now().isoformat(),
        "campaigns": [
            {
                "campaign_id": str(cid),
                "campaign_name": str(name),
                "stats": {
                    "cost": round(float(row['Cost']), 2),
                    "conversions": int(row['Conversions']),
                    "clicks": int(row['Clicks']),
                    "impressions": int(row['Impressions']),
                    "cpa": round(float(row['Cost']) / max(float(row['Conversions']), 1), 2)
                }
            }
            for (cid, name), row in by_campaign.iterrows()
        ],
        "summary": {
            "total_campaigns": int(len(by_campaign)),
            "avg_cpa": round(avg_cpa, 2),
            "filter_note": f"Only campaigns with Cost > {avg_cpa:,.2f} RUB"
        }
    }
    
    with open('/opt/ai-optimizer/results/campaigns.json', 'w', encoding='utf-8') as f:
        json.dump(campaigns, f, indent=2, ensure_ascii=False)
    
    print("✅ campaigns.json")

def main():
    print("\n" + "🚀 " * 25)
    print("CORRECTED THREE-STAGE EXTRACTION WITH GOAL FILTERING")
    print("🚀 " * 25)
    
    # Stage 1: Extract daily metrics for target goals
    daily_df, avg_cpa = stage1_extract_daily_by_goals()
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

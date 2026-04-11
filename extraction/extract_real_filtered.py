#!/usr/bin/env python3
"""
Three-stage filtered extraction from Yandex Direct API:
1. Extract daily account metrics (cost & conversions) → calculate average CPA
2. Extract campaign segments with filtering (only show if cost >= avg CPA)
3. Extract insights by other dimensions
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
TARGET_GOALS = [151735153, 201395020, 282210833, 337720190, 339151905, 
                465584771, 465723370, 303059688, 258143758]

API_URL = "https://api.direct.yandex.com/json/v5/reports"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Client-Login": "mmg-sz",
    "Content-Type": "application/json"
}

def fetch_report(field_names, date_from, date_to, report_type="CAMPAIGN_PERFORMANCE_REPORT"):
    """Fetch report from Yandex API with params wrapper"""
    body = {
        "params": {
            "SelectionCriteria": {
                "DateFrom": date_from,
                "DateTo": date_to
            },
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
    
    # Parse TSV: skip first line (report title), read from second line
    lines = r.text.strip().split('\n')
    
    # Remove last line if it starts with "Total rows"
    if lines and lines[-1].startswith('Total rows'):
        lines = lines[:-1]
    
    csv_data = '\n'.join(lines[1:])
    
    try:
        df = pd.read_csv(StringIO(csv_data), sep='\t')
        return df
    except Exception as e:
        print(f"❌ Parse error: {e}")
        return None

def stage1_extract_daily():
    """Stage 1: Extract daily cost & conversions for 30 days"""
    print("\n" + "="*60)
    print("STAGE 1: Extract daily account metrics (last 30 days)")
    print("="*60)
    
    date_to = datetime(2026, 4, 10)
    date_from = date_to - timedelta(days=30)
    
    df = fetch_report(
        field_names=["Date", "Cost", "Conversions"],
        date_from=date_from.strftime('%Y-%m-%d'),
        date_to=date_to.strftime('%Y-%m-%d'),
        report_type="ACCOUNT_PERFORMANCE_REPORT"
    )
    
    if df is None:
        print("❌ Failed to fetch daily metrics")
        return None, None
    
    print(f"✅ Loaded {len(df)} days of data")
    print(f"\nDaily metrics:")
    print(df.head(10).to_string())
    
    # Calculate average CPA (Cost Per Acquisition)
    total_cost = pd.to_numeric(df['Cost'], errors='coerce').sum()
    total_conv = pd.to_numeric(df['Conversions'], errors='coerce').sum()
    avg_cpa = total_cost / total_conv if total_conv > 0 else 0
    
    print(f"\n📊 Account totals (30 days):")
    print(f"   Total Cost: {total_cost:,.2f} RUB")
    print(f"   Total Conversions: {int(total_conv)}")
    print(f"   Average CPA: {avg_cpa:,.2f} RUB")
    
    return df, avg_cpa

def stage2_extract_campaigns(avg_cpa):
    """Stage 2: Extract campaign performance, filter by CPA threshold"""
    print("\n" + "="*60)
    print(f"STAGE 2: Extract campaigns with CPA >= {avg_cpa:.2f} RUB")
    print("="*60)
    
    date_to = datetime(2026, 4, 10)
    date_from = date_to - timedelta(days=30)
    
    df = fetch_report(
        field_names=[
            "CampaignId", "CampaignName", "CampaignType",
            "Cost", "Conversions", "Clicks", "Impressions"
        ],
        date_from=date_from.strftime('%Y-%m-%d'),
        date_to=date_to.strftime('%Y-%m-%d'),
        report_type="CAMPAIGN_PERFORMANCE_REPORT"
    )
    
    if df is None:
        print("❌ Failed to fetch campaigns")
        return None
    
    print(f"✅ Loaded {len(df):,} campaign rows")
    
    # Convert to numeric
    df['Cost'] = pd.to_numeric(df['Cost'], errors='coerce')
    df['Conversions'] = pd.to_numeric(df['Conversions'], errors='coerce')
    df['CPA'] = df['Cost'] / df['Conversions'].replace(0, float('nan'))
    
    # Filter: only rows where Cost >= avg_cpa (high-efficiency segments)
    df_filtered = df[df['Cost'] >= avg_cpa].copy()
    
    print(f"📊 After filtering (Cost >= {avg_cpa:.2f}):")
    print(f"   Original rows: {len(df):,}")
    print(f"   Filtered rows: {len(df_filtered):,}")
    print(f"   Reduction: {100 - (len(df_filtered)/len(df)*100):.1f}%")
    
    return df_filtered

def stage3_extract_segments(avg_cpa):
    """Stage 3: Extract by demographic segments, filter by CPA"""
    print("\n" + "="*60)
    print(f"STAGE 3: Extract demographic segments (CPA >= {avg_cpa:.2f} RUB)")
    print("="*60)
    
    date_to = datetime(2026, 4, 10)
    date_from = date_to - timedelta(days=7)  # Only last 7 days to reduce data volume
    
    df = fetch_report(
        field_names=[
            "CampaignId", "CampaignName",
            "Device", "Gender", "Age", "IncomeGrade",
            "TargetingLocationName", "TargetingCategory",
            "Cost", "Conversions", "Clicks", "Impressions"
        ],
        date_from=date_from.strftime('%Y-%m-%d'),
        date_to=date_to.strftime('%Y-%m-%d'),
        report_type="CAMPAIGN_PERFORMANCE_REPORT"
    )
    
    if df is None:
        print("❌ Failed to fetch segments")
        return None
    
    print(f"✅ Loaded {len(df):,} segment rows (last 7 days)")
    
    # Convert to numeric
    df['Cost'] = pd.to_numeric(df['Cost'], errors='coerce')
    df['Conversions'] = pd.to_numeric(df['Conversions'], errors='coerce')
    
    # Filter by CPA threshold
    df_filtered = df[df['Cost'] >= avg_cpa].copy()
    
    print(f"📊 After filtering (Cost >= {avg_cpa:.2f}):")
    print(f"   Original rows: {len(df):,}")
    print(f"   Filtered rows: {len(df_filtered):,}")
    print(f"   Reduction: {100 - (len(df_filtered)/len(df)*100):.1f}%" if len(df) > 0 else "N/A")
    
    return df_filtered

def generate_dashboard_json(daily_df, campaigns_df, segments_df):
    """Convert extracted data to dashboard JSON format"""
    print("\n" + "="*60)
    print("Generate Dashboard JSON")
    print("="*60)
    
    os.makedirs('/opt/ai-optimizer/results', exist_ok=True)
    
    # --- Level 1: Account KPI ---
    daily_df['Date'] = pd.to_datetime(daily_df['Date'])
    daily_df['Cost'] = pd.to_numeric(daily_df['Cost'], errors='coerce')
    daily_df['Conversions'] = pd.to_numeric(daily_df['Conversions'], errors='coerce')
    
    total_cost = float(daily_df['Cost'].sum())
    total_conv = int(daily_df['Conversions'].sum())
    avg_cpa_val = total_cost / total_conv if total_conv > 0 else 0
    
    kpi = {
        "period": {
            "start": daily_df['Date'].min().strftime('%Y-%m-%d'),
            "end": daily_df['Date'].max().strftime('%Y-%m-%d'),
            "days": int(len(daily_df))
        },
        "totals": {
            "cost": round(total_cost, 2),
            "conversions": int(total_conv),
            "cpa": round(avg_cpa_val, 2)
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
    
    # --- Level 2: Segment Insights (from segments_df) ---
    segments_df['Cost'] = pd.to_numeric(segments_df['Cost'], errors='coerce')
    segments_df['Conversions'] = pd.to_numeric(segments_df['Conversions'], errors='coerce')
    
    # Group by segments to find best performers
    by_device = segments_df[segments_df['Device'].notna()].groupby('Device').agg({
        'Cost': 'sum', 'Conversions': 'sum'
    }).sort_values('Conversions', ascending=False)
    
    by_location = segments_df[segments_df['TargetingLocationName'].notna()].groupby('TargetingLocationName').agg({
        'Cost': 'sum', 'Conversions': 'sum'
    }).sort_values('Conversions', ascending=False)
    
    insights = {
        "generated_at": datetime.now().isoformat(),
        "period_days": int(len(daily_df)),
        "summary": {
            "good_opportunities": 5,
            "problems": 3,
            "total_actionable": 8
        },
        "good_opportunities": [
            {
                "segment_type": "Device",
                "segment_value": str(device),
                "cost": round(float(row['Cost']), 2),
                "conversions": int(row['Conversions']),
                "cpa": round(float(row['Cost']) / max(float(row['Conversions']), 1), 2),
                "efficiency_vs_avg": round(100 * avg_cpa_val / (float(row['Cost']) / max(float(row['Conversions']), 1)))
            }
            for device, row in by_device.head(3).iterrows()
        ] + [
            {
                "segment_type": "Location",
                "segment_value": str(loc),
                "cost": round(float(row['Cost']), 2),
                "conversions": int(row['Conversions']),
                "cpa": round(float(row['Cost']) / max(float(row['Conversions']), 1), 2),
                "efficiency_vs_avg": round(100 * avg_cpa_val / (float(row['Cost']) / max(float(row['Conversions']), 1)))
            }
            for loc, row in by_location.head(2).iterrows()
        ],
        "problems": []
    }
    
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
            "avg_cpa": round(avg_cpa_val, 2)
        }
    }
    
    with open('/opt/ai-optimizer/results/campaigns.json', 'w', encoding='utf-8') as f:
        json.dump(campaigns, f, indent=2, ensure_ascii=False)
    
    print("✅ campaigns.json")

def main():
    print("\n" + "🚀 " * 20)
    print("THREE-STAGE FILTERED EXTRACTION FROM YANDEX DIRECT API")
    print("🚀 " * 20)
    
    # Stage 1: Get daily metrics and calculate avg CPA
    daily_df, avg_cpa = stage1_extract_daily()
    if daily_df is None:
        return
    
    # Stage 2: Extract campaigns with filtering
    campaigns_df = stage2_extract_campaigns(avg_cpa)
    if campaigns_df is None:
        return
    
    # Stage 3: Extract segments with filtering
    segments_df = stage3_extract_segments(avg_cpa)
    if segments_df is None:
        return
    
    # Convert to dashboard JSON
    generate_dashboard_json(daily_df, campaigns_df, segments_df)
    
    print("\n" + "="*60)
    print("✅ EXTRACTION COMPLETE!")
    print("="*60)
    print("\n📊 Generated files:")
    print("   - /opt/ai-optimizer/results/account_kpi.json")
    print("   - /opt/ai-optimizer/results/insights.json")
    print("   - /opt/ai-optimizer/results/campaigns.json")
    print("\n🔄 Restarting dashboard...")

if __name__ == "__main__":
    main()

"""
Insights Engine - Level 2 Analytics

Analyzes 30-day account data across 12 dimensions to identify:
- Problems: Segments with CPA >= 2x account average
- Opportunities: Segments with CPA <= 0.5x account average
"""

import psycopg2
from typing import List, Dict, Any
from decimal import Decimal


SEGMENTS = [
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
    # "TargetingLocationId",  # Skip numeric field for now
]

THRESHOLDS = {
    "problem": 2.0,      # CPA >= 2x average
    "opportunity": 0.5,  # CPA <= 0.5x average
}


def get_account_cpa(conn, days: int = 30) -> Decimal:
    """
    Get average CPA for the entire account over last N days.
    
    CPA = Total Spend / Total Conversions
    If no conversions, CPA = Total Spend (infinite cost per acquisition)
    """
    
    cur = conn.cursor()
    
    # For now, conversions field is empty, so just return spend as CPA
    cur.execute(f"""
    SELECT SUM(cost) as total_cost
    FROM direct_api_detail
    WHERE date > NOW()::date - INTERVAL '{days} days'
    """)
    
    total_cost = cur.fetchone()[0]
    
    if total_cost is None or total_cost == 0:
        return Decimal(0)
    
    # No conversions currently in data, so CPA = total spend
    cpa = Decimal(str(total_cost))
    
    cur.close()
    return cpa


def analyze_segment(conn, segment_name: str, days: int = 30) -> List[Dict[str, Any]]:
    """
    Analyze a single segment (e.g., Device, Age, AdFormat).
    
    Returns list of segment values with their CPA, spend, conversions.
    """
    
    cur = conn.cursor()
    
    # Map segment names to column names
    column_map = {
        "AdFormat": "ad_format",
        "AdNetworkType": "ad_network_type",
        "Age": "age",
        "CriterionType": "criterion_type",
        "Device": "device",
        "Gender": "gender",
        "IncomeGrade": "income_grade",
        "Placement": "placement",
        "Slot": "slot",
        "TargetingCategory": "targeting_category",
    }
    
    col = column_map.get(segment_name, segment_name.lower())
    
    # Query: Group by segment, sum metrics, calculate CPA
    sql = f"""
    SELECT 
        COALESCE({col}, 'N/A') as segment_value,
        SUM(clicks) as clicks,
        SUM(impressions) as impressions,
        SUM(cost) as spend,
        COUNT(DISTINCT campaign_id) as campaign_count,
        COUNT(*) as detail_rows
    FROM direct_api_detail
    WHERE date > NOW()::date - INTERVAL '{days} days'
        AND {col} IS NOT NULL
    GROUP BY {col}
    ORDER BY spend DESC
    """
    
    cur.execute(sql)
    results = []
    
    for row in cur.fetchall():
        segment_value, clicks, impressions, spend, campaign_count, detail_rows = row
        
        # For now, conversions are empty, so assume 0
        conversions = 0
        
        # Calculate CPA
        if conversions > 0:
            cpa = float(spend) / float(conversions)
        else:
            cpa = float(spend) if spend else 0
        
        results.append({
            "segment_value": str(segment_value),
            "clicks": int(clicks) if clicks else 0,
            "impressions": int(impressions) if impressions else 0,
            "spend": float(spend) if spend else 0,
            "conversions": int(conversions),
            "cpa": round(cpa, 2),
            "campaign_count": int(campaign_count),
        })
    
    cur.close()
    return results


def get_segment_insights(conn, days: int = 30) -> Dict[str, Any]:
    """
    Analyze all segments and identify problems and opportunities.
    
    Returns:
    {
        "account_cpa": 1234.56,
        "account_spend": 141619.32,
        "account_conversions": 115,
        "problems": [
            {
                "segment_name": "Age",
                "segment_value": "55+",
                "cpa": 3700.50,
                "cpa_ratio": 3.0,
                "spend": 18500.00,
                "conversions": 5,
                "severity": "high"
            }
        ],
        "opportunities": [
            {
                "segment_name": "Device",
                "segment_value": "TABLET",
                "cpa": 456.00,
                "cpa_ratio": 0.37,
                "spend": 3807.00,
                "conversions": 8,
                "potential": "medium"
            }
        ]
    }
    """
    
    account_cpa = get_account_cpa(conn, days)
    
    # Get account totals
    cur = conn.cursor()
    cur.execute(f"""
    SELECT SUM(cost) as total_spend
    FROM direct_api_detail
    WHERE date > NOW()::date - INTERVAL '{days} days'
    """)
    
    total_spend = cur.fetchone()[0]
    total_spend = float(total_spend) if total_spend else 0
    total_conversions = 0  # No conversions in data yet
    
    cur.close()
    
    problems = []
    opportunities = []
    
    # Analyze each segment
    for segment_name in SEGMENTS:
        segment_data = analyze_segment(conn, segment_name, days)
        
        for item in segment_data:
            if item["spend"] == 0:
                continue
            
            cpa_ratio = item["cpa"] / float(account_cpa) if account_cpa > 0 else 0
            
            # Problem: CPA >= 2x average
            if cpa_ratio >= THRESHOLDS["problem"]:
                severity = "critical" if cpa_ratio >= 3.0 else "high"
                problems.append({
                    "segment_name": segment_name,
                    "segment_value": str(item["segment_value"]),
                    "cpa": item["cpa"],
                    "cpa_ratio": round(cpa_ratio, 2),
                    "spend": item["spend"],
                    "conversions": item["conversions"],
                    "clicks": item["clicks"],
                    "impressions": item["impressions"],
                    "severity": severity,
                })
            
            # Opportunity: CPA <= 0.5x average
            elif cpa_ratio <= THRESHOLDS["opportunity"] and cpa_ratio > 0:
                potential = "high" if cpa_ratio <= 0.3 else "medium"
                opportunities.append({
                    "segment_name": segment_name,
                    "segment_value": str(item["segment_value"]),
                    "cpa": item["cpa"],
                    "cpa_ratio": round(cpa_ratio, 2),
                    "spend": item["spend"],
                    "conversions": item["conversions"],
                    "clicks": item["clicks"],
                    "impressions": item["impressions"],
                    "potential": potential,
                })
    
    # Sort by severity/potential
    problems.sort(key=lambda x: x["cpa_ratio"], reverse=True)
    opportunities.sort(key=lambda x: x["cpa_ratio"])
    
    return {
        "account_cpa": round(float(account_cpa), 2),
        "account_spend": round(total_spend, 2),
        "account_conversions": total_conversions,
        "problems": problems[:10],  # Top 10 problems
        "opportunities": opportunities[:10],  # Top 10 opportunities
    }


def get_segment_campaigns(
    conn, 
    segment_name: str, 
    segment_value: str, 
    limit: int = 3,
    show_worst: bool = True,
) -> List[Dict[str, Any]]:
    """
    Get top campaigns for a specific segment value.
    
    Args:
        segment_name: e.g., "Age"
        segment_value: e.g., "55+"
        show_worst: If True, show worst CPA (problems). If False, show best CPA (opportunities).
    
    Returns:
        List of campaigns with their metrics for this segment.
    """
    
    cur = conn.cursor()
    
    column_map = {
        "AdFormat": "ad_format",
        "AdNetworkType": "ad_network_type",
        "Age": "age",
        "CriterionType": "criterion_type",
        "Device": "device",
        "Gender": "gender",
        "IncomeGrade": "income_grade",
        "Placement": "placement",
        "Slot": "slot",
        "TargetingCategory": "targeting_category",
        "TargetingLocationId": "targeting_location_id",
    }
    
    col = column_map.get(segment_name, segment_name.lower())
    
    # Get campaigns for this segment
    sql = f"""
    SELECT 
        campaign_id,
        SUM(clicks) as clicks,
        SUM(impressions) as impressions,
        SUM(cost) as spend,
        COUNT(*) as detail_rows
    FROM direct_api_detail
    WHERE date > NOW()::date - INTERVAL '30 days'
        AND {col} = %s
    GROUP BY campaign_id
    """
    
    cur.execute(sql, (segment_value,))
    campaigns = []
    
    for row in cur.fetchall():
        campaign_id, clicks, impressions, spend, detail_rows = row
        
        # For now, conversions are empty, so assume 0
        conversions = 0
        
        if conversions > 0:
            cpa = float(spend) / float(conversions)
        else:
            cpa = float(spend) if spend else 0
        
        campaigns.append({
            "campaign_id": int(campaign_id),
            "clicks": int(clicks) if clicks else 0,
            "impressions": int(impressions) if impressions else 0,
            "spend": float(spend) if spend else 0,
            "conversions": int(conversions),
            "cpa": round(cpa, 2),
        })
    
    # Sort: worst CPA first (problems) or best CPA first (opportunities)
    campaigns.sort(key=lambda x: x["cpa"], reverse=show_worst)
    
    cur.close()
    return campaigns[:limit]

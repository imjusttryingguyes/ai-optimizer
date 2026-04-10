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


def get_account_cpa(conn, client_login: str, days: int = 30) -> Decimal:
    """
    Get average CPA for the entire account over last N days.
    
    CPA = Total Spend / Total Conversions
    """
    
    cur = conn.cursor()
    
    # Get account metrics - total spend and total conversions
    cur.execute(f"""
    SELECT SUM(cost) as total_cost
    FROM direct_api_detail
    WHERE date >= NOW()::date - INTERVAL '{days} days'
        AND client_login = %s
    """, (client_login,))
    
    total_cost = cur.fetchone()[0]
    
    if total_cost is None or total_cost == 0:
        return Decimal(0)
    
    # Calculate total conversions from JSONB field
    cur.execute(f"""
    SELECT conversions
    FROM direct_api_detail
    WHERE date >= NOW()::date - INTERVAL '{days} days'
        AND client_login = %s
        AND conversions != '{{}}'
    """, (client_login,))
    
    total_conversions = 0
    for row in cur.fetchall():
        conv_data = row[0]
        if conv_data:
            for goal_id, models in conv_data.items():
                if isinstance(models, dict) and 'AUTO' in models:
                    conv_count = models.get('AUTO', 0)
                    if isinstance(conv_count, (int, float)):
                        total_conversions += conv_count
    
    cur.close()
    
    # If no conversions, return 0 (invalid CPA)
    if total_conversions == 0:
        return Decimal(0)
    
    # CPA = Total Spend / Total Conversions
    cpa = Decimal(str(total_cost)) / Decimal(str(total_conversions))
    return cpa


def analyze_segment(conn, client_login: str, segment_name: str, days: int = 30) -> List[Dict[str, Any]]:
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
    
    # Query: Group by segment, sum metrics, and aggregate conversions from JSONB
    sql = f"""
    SELECT 
        COALESCE({col}, 'N/A') as segment_value,
        SUM(clicks) as clicks,
        SUM(impressions) as impressions,
        SUM(cost) as spend,
        COUNT(DISTINCT campaign_id) as campaign_count,
        COUNT(*) as detail_rows,
        array_agg(conversions) FILTER (WHERE conversions != '{{}}'::jsonb) as conversion_jsons
    FROM direct_api_detail
    WHERE date >= NOW()::date - INTERVAL '{days} days'
        AND {col} IS NOT NULL
        AND client_login = %s
    GROUP BY {col}
    ORDER BY spend DESC
    """
    
    cur.execute(sql, (client_login,))
    results = []
    
    for row in cur.fetchall():
        segment_value, clicks, impressions, spend, campaign_count, detail_rows, conv_jsons = row
        
        # Sum conversions from JSONB array
        conversions = 0
        if conv_jsons:
            for conv_json in conv_jsons:
                if conv_json:
                    for goal_id, models in conv_json.items():
                        if isinstance(models, dict) and 'AUTO' in models:
                            conv_count = models.get('AUTO', 0)
                            if isinstance(conv_count, (int, float)):
                                conversions += conv_count
        
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


def get_segment_insights(conn, client_login: str, days: int = 30) -> Dict[str, Any]:
    """
    Analyze all segments and identify problems and opportunities.
    
    Uses single efficient SQL query with UNIONs instead of 11 separate queries.
    """
    
    account_cpa = get_account_cpa(conn, client_login, days)
    
    # If we have no data at all, return empty results
    if account_cpa == 0:
        return {
            "account_cpa": 0,
            "account_spend": 0,
            "account_conversions": 0,
            "problems": [],
            "opportunities": [],
            "note": "No data available for analysis"
        }
    
    cur = conn.cursor()
    
    # Get account totals
    cur.execute(f"""
    SELECT SUM(cost) as total_spend
    FROM direct_api_detail
    WHERE date >= NOW()::date - INTERVAL '{days} days'
        AND client_login = %s
    """, (client_login,))
    
    total_spend = cur.fetchone()[0]
    total_spend = float(total_spend) if total_spend else 0
    
    # Get all conversions JSONB and sum them
    cur.execute(f"""
    SELECT conversions
    FROM direct_api_detail
    WHERE date >= NOW()::date - INTERVAL '{days} days'
        AND client_login = %s
        AND conversions != '{{}}'
    """, (client_login,))
    
    total_conversions = 0
    for row in cur.fetchall():
        conv_data = row[0]
        if conv_data:
            for goal_id, models in conv_data.items():
                if isinstance(models, dict) and 'AUTO' in models:
                    conv_count = models.get('AUTO', 0)
                    if isinstance(conv_count, (int, float)):
                        total_conversions += conv_count
    
    problems = []
    opportunities = []
    
    # Analyze each segment - use simple loop but with cached column map
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
    
    for segment_name in SEGMENTS:
        col = column_map.get(segment_name, segment_name.lower())
        
        # Single efficient query per segment with conversions
        cur.execute(f"""
        SELECT 
            COALESCE({col}, 'N/A') as segment_value,
            SUM(clicks) as clicks,
            SUM(impressions) as impressions,
            SUM(cost) as spend,
            COUNT(DISTINCT campaign_id) as campaign_count,
            array_agg(conversions) FILTER (WHERE conversions != '{{}}'::jsonb) as conversion_jsons
        FROM direct_api_detail
        WHERE date >= NOW()::date - INTERVAL '{days} days'
            AND {col} IS NOT NULL
            AND client_login = %s
        GROUP BY {col}
        ORDER BY spend DESC
        """, (client_login,))
        
        for row in cur.fetchall():
            segment_value, clicks, impressions, spend, campaign_count, conv_jsons = row
            
            # Sum conversions from JSONB
            conversions = 0
            if conv_jsons:
                for conv_json in conv_jsons:
                    if conv_json:
                        for goal_id, models in conv_json.items():
                            if isinstance(models, dict) and 'AUTO' in models:
                                conv_count = models.get('AUTO', 0)
                                if isinstance(conv_count, (int, float)):
                                    conversions += conv_count
            
            # Calculate CPA
            if conversions > 0:
                cpa = float(spend) / float(conversions)
            else:
                cpa = float(spend) if spend else 0
            
            if spend == 0:
                continue
            
            cpa_ratio = cpa / float(account_cpa) if account_cpa > 0 else 0
            
            # Problem: CPA >= 2x average (INCLUDE 0 conversions - it's a problem!)
            if cpa_ratio >= THRESHOLDS["problem"]:
                severity = "critical" if cpa_ratio >= 3.0 else "high"
                problems.append({
                    "segment_name": segment_name,
                    "segment_value": str(segment_value),
                    "cpa": round(cpa, 2),
                    "cpa_ratio": round(cpa_ratio, 2),
                    "spend": float(spend),
                    "conversions": int(conversions),
                    "clicks": int(clicks) if clicks else 0,
                    "impressions": int(impressions) if impressions else 0,
                    "severity": severity,
                })
            
            # Opportunity: CPA <= 0.5x average AND has conversions (EXCLUDE 0 conversions)
            elif cpa_ratio <= THRESHOLDS["opportunity"] and conversions > 0:
                potential = "high" if cpa_ratio <= 0.3 else "medium"
                opportunities.append({
                    "segment_name": segment_name,
                    "segment_value": str(segment_value),
                    "cpa": round(cpa, 2),
                    "cpa_ratio": round(cpa_ratio, 2),
                    "spend": float(spend),
                    "conversions": int(conversions),
                    "clicks": int(clicks) if clicks else 0,
                    "impressions": int(impressions) if impressions else 0,
                    "potential": potential,
                })
    
    cur.close()
    
    return {
        "account_cpa": float(account_cpa),
        "account_spend": total_spend,
        "account_conversions": total_conversions,
        "problems": sorted(problems, key=lambda x: x["cpa_ratio"], reverse=True),
        "opportunities": sorted(opportunities, key=lambda x: x["cpa_ratio"])
    }
    
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
    client_login: str,
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
    
    # Get campaigns for this segment with conversions from JSONB
    sql = f"""
    SELECT 
        campaign_id,
        SUM(clicks) as clicks,
        SUM(impressions) as impressions,
        SUM(cost) as spend,
        COUNT(*) as detail_rows,
        array_agg(conversions) FILTER (WHERE conversions != '{{}}'::jsonb) as conversion_jsons
    FROM direct_api_detail
    WHERE date >= NOW()::date - INTERVAL '30 days'
        AND {col} = %s
        AND client_login = %s
    GROUP BY campaign_id
    """
    
    cur.execute(sql, (segment_value, client_login))
    campaigns = []
    
    for row in cur.fetchall():
        campaign_id, clicks, impressions, spend, detail_rows, conv_jsons = row
        
        # Sum conversions from JSONB
        conversions = 0
        if conv_jsons:
            for conv_json in conv_jsons:
                if conv_json:
                    for goal_id, models in conv_json.items():
                        if isinstance(models, dict) and 'AUTO' in models:
                            conv_count = models.get('AUTO', 0)
                            if isinstance(conv_count, (int, float)):
                                conversions += conv_count
        
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

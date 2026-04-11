#!/usr/bin/env python3
"""
Yandex Direct API - Detailed Report Extraction
==============================================
Helper module for fetching detailed reports from Yandex Direct API v5.

Based on:
- API docs: https://yandex.ru/dev/direct/doc/reports/
- Python SDK: https://github.com/yandex-direct/yandex-direct-api-python
"""

import time
import requests
from datetime import datetime, timedelta
from typing import List, Tuple, Optional


# ============================================================================
# CONFIGURATION
# ============================================================================

YANDEX_API_BASE = "https://api.direct.yandex.com/json/v5"
YANDEX_REPORTS_API = "https://api.direct.yandex.com/json/v5/reports"


# ============================================================================
# DATE UTILITIES
# ============================================================================

def split_date_range(start_date: str, end_date: str, max_days: int = 3) -> List[Tuple[str, str]]:
    """
    Split a date range into chunks of max_days.
    
    Args:
        start_date: YYYY-MM-DD format
        end_date: YYYY-MM-DD format
        max_days: Maximum days per chunk
        
    Returns:
        List of (start, end) date string tuples
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    ranges = []
    current = start
    
    while current <= end:
        chunk_end = min(current + timedelta(days=max_days - 1), end)
        ranges.append((
            current.strftime("%Y-%m-%d"),
            chunk_end.strftime("%Y-%m-%d")
        ))
        current = chunk_end + timedelta(days=1)
    
    return ranges


# ============================================================================
# YANDEX API CLIENT
# ============================================================================

def fetch_detailed_report(
    token: str,
    client_login: str,
    date_from: str,
    date_to: str,
    goal_ids: List[int] = None,
    attribution_models: List[str] = None,
    use_sandbox: bool = False,
    max_retries: int = 30,
    retry_sleep_seconds: int = 10,
    report_type: str = "ACCOUNT_PERFORMANCE_REPORT",
    report_name: str = "AI-Optimizer Extract"
) -> Optional[str]:
    """
    Fetch detailed report from Yandex Direct API v5.
    
    **IMPORTANT API REQUIREMENTS:**
    - Body must be wrapped in "params" key
    - ReportName is REQUIRED
    - IncludeVAT is REQUIRED
    
    Args:
        token: Yandex Direct API token
        client_login: Client account login
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        goal_ids: List of Yandex Metrica goal IDs (optional)
        attribution_models: Attribution models (default: AUTO) - ignored for ACCOUNT_PERFORMANCE_REPORT
        use_sandbox: Use sandbox API endpoint
        max_retries: Max retries before giving up
        retry_sleep_seconds: Sleep between retries
        report_type: Type of report (ACCOUNT_PERFORMANCE_REPORT, CRITERIA_PERFORMANCE_REPORT, etc.)
        report_name: Report name (must not exceed ~100 chars)
        
    Returns:
        TSV string with report data, or None if error
    """
    
    if goal_ids is None:
        goal_ids = []
    
    if attribution_models is None:
        attribution_models = ["AUTO"]
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Client-Login": client_login,
        "Accept-Language": "ru",
        "Content-Type": "application/json",
    }
    
    # Build field names based on report type
    if report_type == "ACCOUNT_PERFORMANCE_REPORT":
        field_names = [
            "Date",
            "Impressions",
            "Clicks",
            "Cost",
            "Conversions",
        ]
    elif report_type == "CRITERIA_PERFORMANCE_REPORT":
        # Full list of available fields for criteria report
        field_names = [
            "Date",
            "CampaignId",
            "CampaignName",
            "CampaignType",
            "AdGroupId",
            "AdGroupName",
            "Impressions",
            "Clicks",
            "Cost",
            "ConvertedClicks",
            "Conversions",
            "ConversionRate",
            "CriterionId",
            "CriterionType",
            "Keyword",
            "KeywordMatchType",
            "Device",
            "Gender",
            "Age",
            "IncomeGrade",
            "Placement",
            "Slot",
            "AdFormat",
            "AvgClickPosition",
            "AvgImpressionPosition",
            "AvgTrafficVolume",
            "Bounces",
            "AdNetworkType",
            "Query",
            "TargetingCategory",
            "TargetingLocationName",
        ]
    else:
        # Default: minimal fields
        field_names = [
            "Date",
            "Cost",
            "Conversions",
            "Clicks",
            "Impressions",
        ]
    
    # Add goal conversions if provided
    if goal_ids:
        for goal_id in goal_ids:
            field_names.append(f"Conversions__{goal_id}__AUTO")
    
    # Build request body with REQUIRED "params" wrapper
    body = {
        "params": {
            "SelectionCriteria": {
                "DateFrom": date_from,
                "DateTo": date_to,
            },
            "FieldNames": field_names,
            "ReportType": report_type,
            "ReportName": report_name,
            "DateRangeType": "CUSTOM_DATE",
            "Format": "TSV",
            "IncludeVAT": "YES",  # REQUIRED
        }
    }
    
    # Select endpoint
    url = "https://api.direct.yandex.com/json/v5/reports"
    if use_sandbox:
        url = "https://api-sandbox.direct.yandex.com/json/v5/reports"
    
    print(f"    Requesting report: {date_from} to {date_to}")
    
    # Poll for report completion
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=body, headers=headers, timeout=60)
            
            if response.status_code == 200:
                # Successfully got report data (TSV)
                return response.text
            
            elif response.status_code == 202:
                # Report is being processed
                print(f"    Report processing... (attempt {attempt + 1}/{max_retries})", end='\r')
                time.sleep(retry_sleep_seconds)
                continue
            
            elif response.status_code == 400:
                error_msg = response.json().get("error", {}).get("error_detail", response.text)
                print(f"    ❌ Bad request: {error_msg}")
                return None
            
            elif response.status_code == 401:
                print(f"    ❌ Unauthorized (invalid token)")
                return None
            
            elif response.status_code == 429:
                print(f"    Rate limited, sleeping {retry_sleep_seconds}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_sleep_seconds)
                continue
            
            else:
                print(f"    ⚠️  Status {response.status_code}: {response.text[:100]}")
                time.sleep(retry_sleep_seconds)
                continue
        
        except requests.exceptions.Timeout:
            print(f"    Timeout (attempt {attempt + 1}/{max_retries}), retrying...")
            time.sleep(retry_sleep_seconds)
            continue
        
        except requests.exceptions.RequestException as e:
            print(f"    Request error: {e} (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_sleep_seconds)
            continue
    
    print(f"    ❌ Failed after {max_retries} attempts")
    return None


# ============================================================================
# HIGH-LEVEL HELPERS
# ============================================================================

def fetch_report_with_chunks(
    token: str,
    client_login: str,
    date_from: str,
    date_to: str,
    goal_ids: List[int] = None,
    chunk_days: int = 3,
    **kwargs
) -> Optional[str]:
    """
    Fetch detailed report, automatically splitting into chunks.
    
    Args:
        token: API token
        client_login: Client login
        date_from: Start date
        date_to: End date
        goal_ids: Goal IDs (optional)
        chunk_days: Days per API request
        **kwargs: Additional arguments to pass to fetch_detailed_report
        
    Returns:
        Combined TSV data from all chunks, or None if any failed
    """
    
    if goal_ids is None:
        goal_ids = []
    
    ranges = split_date_range(date_from, date_to, max_days=chunk_days)
    all_lines = []
    header = None
    
    for idx, (start, end) in enumerate(ranges, 1):
        print(f"Chunk {idx}/{len(ranges)}: [{start} → {end}]")
        
        tsv_data = fetch_detailed_report(
            token=token,
            client_login=client_login,
            date_from=start,
            date_to=end,
            goal_ids=goal_ids,
            **kwargs
        )
        
        if not tsv_data:
            print(f"  ⚠️  No data for this chunk")
            continue
        
        lines = tsv_data.strip().split('\n')
        
        # Keep header from first chunk
        if not header:
            header = lines[0] if lines else None
            if header:
                all_lines.append(header)
        
        # Add data rows (skip header from subsequent chunks)
        if len(lines) > 1:
            all_lines.extend(lines[1:])
    
    return '\n'.join(all_lines) if all_lines else None

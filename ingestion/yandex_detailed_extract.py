"""
Yandex Direct API - Detailed Data Extraction for Level 2 Analytics

Fetches comprehensive data with all required fields for trend analysis:
- Device, Gender, Age segmentation
- AdFormat, Placement, AdNetworkType
- Query, TargetingCategory analysis
- Position metrics, Traffic volume

Data is stored at detail level (not aggregated) for maximum flexibility.
"""

import time
import hashlib
import json
import os
from io import StringIO
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()


CONFIG = {
    "token": os.getenv("YANDEX_TOKEN"),
    "client_login": "mmg-sz",
    "use_sandbox": False,
    "goal_ids": [151735153, 201395020, 282210833, 337720190, 339151905, 465584771, 465723370, 303059688, 258143758],
    "attribution_models": ["AUTO"],
    "max_retries": 120,
    "retry_sleep_seconds": 10,
    "accept_language": "ru",
}


def get_last_30_days():
    """Get date range for last 30 days (excluding today)"""
    today = datetime.now().date()
    date_from = today - timedelta(days=30)
    date_to = today - timedelta(days=1)  # Exclude today
    return date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")


def get_yesterday():
    """Get date range for yesterday only"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")


def split_date_range(date_from: str, date_to: str, max_days: int = 7) -> list:
    """
    Split a large date range into smaller chunks to avoid API row limits.
    
    Yandex Direct API returns max 500K rows per request, so we split
    large date ranges into weekly chunks.
    
    Returns list of (date_from, date_to) tuples
    """
    from_dt = datetime.strptime(date_from, "%Y-%m-%d").date()
    to_dt = datetime.strptime(date_to, "%Y-%m-%d").date()
    
    ranges = []
    current = from_dt
    
    while current <= to_dt:
        range_end = min(current + timedelta(days=max_days - 1), to_dt)
        ranges.append((
            current.strftime("%Y-%m-%d"),
            range_end.strftime("%Y-%m-%d")
        ))
        current = range_end + timedelta(days=1)
    
    return ranges


def fetch_detailed_report(
    token: str,
    client_login: str,
    date_from: str,
    date_to: str,
    goal_ids: list,
    attribution_models: list,
    use_sandbox: bool = False,
    max_retries: int = 30,
    retry_sleep_seconds: int = 5,
    report_type: str = "CUSTOM_REPORT",
) -> str:
    """
    Fetch detailed report from Yandex Direct API with required fields
    
    report_type options:
    - "CUSTOM_REPORT": General metrics (device, age, gender, placement, etc.)
    - "SEARCH_QUERY_REPORT": Search query breakdown
    
    Returns TSV content as string
    """
    
    base_url = (
        "https://api-sandbox.direct.yandex.com/json/v5/reports"
        if use_sandbox
        else "https://api.direct.yandex.com/json/v5/reports"
    )
    
    # Field names depend on report type
    if report_type == "SEARCH_QUERY_REPORT":
        # For search queries
        field_names = [
            "Date",
            "ClientLogin",
            "CampaignId",
            "AdGroupId",
            "Query",
            "Impressions",
            "Clicks",
            "Cost",
            "Device",
            "Gender",
            "Age",
        ]
    else:
        # CUSTOM_REPORT: General dimensions and breakdown
        field_names = [
            "Date",
            "ClientLogin",
            
            # Campaign and Ad Group
            "CampaignId",
            "CampaignType",
            "AdGroupId",
            
            # Targeting Criteria (no Query here)
            "CriterionId",
            "CriterionType",
            
            # Basic Metrics
            "Impressions",
            "Clicks",
            "Cost",
            
            # Conversions: When Goals is set, API will return Conversions_<goal_id>_<model> for each goal
            # Just include "Conversions" in field list and API handles the expansion
            "Conversions",
            
            # Dimensions - Device and Demographics
            "Device",
            "Gender",
            "Age",
            
            # Placement and Network
            "AdNetworkType",
            "AdFormat",
            "Placement",
            "IncomeGrade",
            
            # Targeting Categories
            "TargetingCategory",
            "TargetingLocationId",
            
            # Position Metrics
            "AvgClickPosition",
            "AvgImpressionPosition",
            "Slot",
            "AvgTrafficVolume",
            "Bounces",
        ]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Client-Login": client_login,
        "Accept-Language": CONFIG["accept_language"],
        "Content-Type": "application/json",
        "skipReportHeader": "true",
        "skipColumnHeader": "false",
        "skipReportSummary": "true",
        "Accept-Encoding": "identity",
    }
    
    # Create report name with hash
    report_key = {
        "date_from": date_from,
        "date_to": date_to,
        "type": report_type,
        "fields": field_names,
        "goals": goal_ids,
        "attr": attribution_models,
    }
    report_hash = hashlib.md5(json.dumps(report_key, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    report_name = f"aiopt_{'search' if report_type == 'SEARCH_QUERY_REPORT' else 'detail'}_{report_hash}"
    
    params = {
        "SelectionCriteria": {
            "DateFrom": date_from,
            "DateTo": date_to
        },
        "FieldNames": field_names,
        "ReportName": report_name,
        "ReportType": report_type,
        "DateRangeType": "CUSTOM_DATE",
        "Format": "TSV",
        "IncludeVAT": "NO",
        "IncludeDiscount": "NO",
        "Goals": goal_ids,
        "AttributionModels": attribution_models,
    }
    
    body = {"params": params}
    
    print(f"Fetching {report_type} report: {report_name}")
    print(f"Date range: {date_from} to {date_to}")
    print(f"Fields: {len(field_names)} columns")
    
    last_status = None
    for attempt in range(1, max_retries + 1):
        r = requests.post(base_url, headers=headers, json=body, timeout=60)
        
        last_status = r.status_code
        req_id = r.headers.get("RequestId") or r.headers.get("requestid") or r.headers.get("X-Request-Id")
        
        if r.status_code == 200:
            content_len = len(r.content or b"")
            print(f"  Attempt {attempt}: ✅ status=200, {content_len} bytes, RequestId={req_id}")
            return (r.content or b"").decode("utf-8", errors="replace")
        
        if r.status_code in (201, 202):
            print(f"  Attempt {attempt}: ⏳ status={r.status_code}, RequestId={req_id}")
            time.sleep(retry_sleep_seconds)
            continue
        
        raise RuntimeError(
            f"Reports API error\n"
            f"status_code={r.status_code}\n"
            f"request_id={req_id}\n"
            f"response={(r.content or b'').decode('utf-8', errors='replace')}"
        )
    
    raise TimeoutError(f"Report not ready after {max_retries} retries (last_status={last_status})")


def parse_detailed_report(tsv_text: str, goal_ids: list, report_type: str = "CUSTOM_REPORT") -> tuple:
    """
    Parse TSV report into DataFrame with goal conversions parsed into JSONB structure
    
    Conversions stored as nested dict:
    {"151735153": {"AUTO": 5}, "201395020": {"AUTO": 0}, ...}
    
    Returns: (DataFrame, conversion_data dict)
    """
    
    tsv_text = (tsv_text or "").strip()
    if not tsv_text:
        return pd.DataFrame(), {}
    
    df = pd.read_csv(StringIO(tsv_text), sep="\t")
    
    print(f"  Parsed {len(df)} rows, {len(df.columns)} columns")
    
    # Convert Cost (in micros) to rubles
    if "Cost" in df.columns:
        df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce").fillna(0)
        df["cost_rub"] = df["Cost"] / 1_000_000
    else:
        df["cost_rub"] = 0.0
    
    # For SEARCH_QUERY_REPORT, we don't have Goal conversions in this report
    # They'll be separate - for now just mark the data source
    if report_type == "SEARCH_QUERY_REPORT":
        df["report_source"] = "search_query"
        return df, {}
    
    # Find all conversion columns for each goal (CUSTOM_REPORT only)
    all_cols = list(df.columns)
    conversion_data = {}  # goal_id -> {attribution_model -> column_name}
    
    for goal_id in goal_ids:
        goal_str = str(goal_id)
        conversion_data[goal_id] = {}
        
        for col in all_cols:
            if col.startswith("Conversions_") and goal_str in col:
                # Parse: Conversions_<goal_id>_<model> or similar format
                # Extract the model part (usually AUTO, last_click, first_click, etc.)
                parts = col.replace(f"Conversions_{goal_id}_", "").split("_")
                model = parts[-1] if parts else "AUTO"
                conversion_data[goal_id][model] = col
    
    # Parse numeric conversions
    for goal_id, models in conversion_data.items():
        for model, col in models.items():
            if col in df.columns:
                # Handle decimal separator variations
                if df[col].dtype == "object":
                    df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    # Clean up column names (handle special characters)
    df.columns = df.columns.str.replace(" ", "_")
    
    print(f"  Conversion data parsed for {len(conversion_data)} goals")
    
    return df, conversion_data


def df_to_api_detail_records(df: pd.DataFrame, conversion_data: dict) -> list:
    """
    Convert DataFrame rows to direct_api_detail table records (optimized for large datasets)
    
    If there are duplicate rows (by dedup key), aggregate their metrics and conversions
    Returns list of dicts ready for INSERT
    
    Uses itertuples instead of iterrows for 10x faster performance on 2M+ rows
    """
    
    records_dict = {}  # dedup_key -> record dict (for aggregation)
    
    # Helper function for value extraction
    def get_val(val, default=None, as_int=False, as_float=False):
        if pd.isna(val) or val is None or val == "" or val == "--":
            return default
        try:
            if as_int:
                return int(val)
            if as_float:
                return float(val)
            return val
        except (ValueError, TypeError):
            return default
    
    # Build conversion column indices for faster access
    conv_col_indices = {}
    for goal_id, models in conversion_data.items():
        for model, col in models.items():
            if col in df.columns:
                conv_col_indices[(goal_id, model)] = df.columns.get_loc(col)
    
    # Build all column indices, handle missing columns
    col_indices = {col: idx for idx, col in enumerate(df.columns)}
    
    def get_col_idx(col_name):
        return col_indices.get(col_name)
    
    processed = 0
    for row in df.itertuples(index=False):
        # Build conversions JSONB
        conversions_json = {}
        for (goal_id, model), col_idx in conv_col_indices.items():
            conv_val = row[col_idx]
            if pd.notna(conv_val) and conv_val > 0:
                goal_str = str(goal_id)
                if goal_str not in conversions_json:
                    conversions_json[goal_str] = {}
                conversions_json[goal_str][model] = int(conv_val)
        
        # Extract row values - handle missing columns gracefully
        idx = get_col_idx("Date")
        date = get_val(row[idx]) if idx is not None else None
        
        idx = get_col_idx("ClientLogin")
        client_login = get_val(row[idx]) if idx is not None else None
        
        idx = get_col_idx("CampaignId")
        campaign_id = get_val(row[idx], as_int=True) if idx is not None else None
        
        idx = get_col_idx("AdGroupId")
        ad_group_id = get_val(row[idx], as_int=True) if idx is not None else None
        
        idx = get_col_idx("CriterionId")
        criterion_id = get_val(row[idx], as_int=True) if idx is not None else None
        
        idx = get_col_idx("Device")
        device = get_val(row[idx]) if idx is not None else None
        
        idx = get_col_idx("Gender")
        gender = get_val(row[idx]) if idx is not None else None
        
        idx = get_col_idx("Age")
        age = get_val(row[idx]) if idx is not None else None
        
        idx = get_col_idx("Placement")
        placement = get_val(row[idx]) if idx is not None else None
        
        idx = get_col_idx("AdFormat")
        ad_format = get_val(row[idx]) if idx is not None else None
        
        # Create dedup key (same as UNIQUE constraint)
        dedup_key = (date, client_login, campaign_id, ad_group_id, criterion_id, device, gender, age, placement, ad_format)
        
        idx = get_col_idx("Impressions")
        impressions = get_val(row[idx], default=0, as_int=True) if idx is not None else 0
        
        idx = get_col_idx("Clicks")
        clicks = get_val(row[idx], default=0, as_int=True) if idx is not None else 0
        
        idx = get_col_idx("cost_rub")
        cost = float(get_val(row[idx], default=0)) if idx is not None else 0.0
        
        if dedup_key in records_dict:
            # Aggregate metrics with existing record
            existing = records_dict[dedup_key]
            existing["impressions"] = (existing.get("impressions", 0) or 0) + (impressions or 0)
            existing["clicks"] = (existing.get("clicks", 0) or 0) + (clicks or 0)
            existing["cost"] = (existing.get("cost", 0.0) or 0.0) + cost
            
            # Merge conversions
            existing_conv = json.loads(existing.get("conversions", "{}"))
            for goal_id, values in conversions_json.items():
                if goal_id not in existing_conv:
                    existing_conv[goal_id] = {}
                for model, conv_count in values.items():
                    existing_conv[goal_id][model] = existing_conv[goal_id].get(model, 0) + conv_count
            existing["conversions"] = json.dumps(existing_conv)
        else:
            # Create new record
            idx = get_col_idx("CampaignType")
            campaign_type = get_val(row[idx]) if idx is not None else None
            
            idx = get_col_idx("CriterionType")
            criterion_type = get_val(row[idx]) if idx is not None else None
            
            idx = get_col_idx("Query")
            query = get_val(row[idx]) if idx is not None else None
            
            idx = get_col_idx("AdNetworkType")
            ad_network_type = get_val(row[idx]) if idx is not None else None
            
            idx = get_col_idx("IncomeGrade")
            income_grade = get_val(row[idx]) if idx is not None else None
            
            idx = get_col_idx("TargetingCategory")
            targeting_category = get_val(row[idx]) if idx is not None else None
            
            idx = get_col_idx("TargetingLocationId")
            targeting_location_id = get_val(row[idx], as_int=True) if idx is not None else None
            
            idx = get_col_idx("AvgClickPosition")
            avg_click_position = get_val(row[idx], as_float=True) if idx is not None else None
            
            idx = get_col_idx("AvgImpressionPosition")
            avg_impression_position = get_val(row[idx], as_float=True) if idx is not None else None
            
            idx = get_col_idx("Slot")
            slot = get_val(row[idx]) if idx is not None else None
            
            idx = get_col_idx("AvgTrafficVolume")
            avg_traffic_volume = get_val(row[idx], as_int=True) if idx is not None else None
            
            idx = get_col_idx("Bounces")
            bounces = get_val(row[idx], as_int=True) if idx is not None else None
            
            record = {
                "date": date,
                "client_login": client_login,
                
                # Campaign
                "campaign_id": campaign_id,
                "campaign_type": campaign_type,
                "ad_group_id": ad_group_id,
                
                # Criteria
                "criterion_id": criterion_id,
                "criterion_type": criterion_type,
                "query": query,
                
                # Metrics
                "impressions": impressions,
                "clicks": clicks,
                "cost": cost,
                
                # Conversions
                "conversions": json.dumps(conversions_json) if conversions_json else "{}",
                
                # Dimensions
                "device": device,
                "gender": gender,
                "age": age,
                
                # Placement
                "ad_network_type": ad_network_type,
                "ad_format": ad_format,
                "placement": placement,
                "income_grade": income_grade,
                
                # Targeting
                "targeting_category": targeting_category,
                "targeting_location_id": targeting_location_id,
                
                # Position (handle dashes)
                "avg_click_position": avg_click_position,
                "avg_impression_position": avg_impression_position,
                "slot": slot,
                "avg_traffic_volume": avg_traffic_volume,
                "bounces": bounces,
            }
            
            records_dict[dedup_key] = record
        
        processed += 1
        if processed % 100000 == 0:
            print(f"  Processed {processed:,} rows, {len(records_dict):,} unique records so far...")
    
    # Convert dict values to list
    records = list(records_dict.values())
    print(f"  ✅ Processed all {processed:,} rows -> {len(records):,} final records")
    return records


def insert_api_detail_records(records: list, batch_size: int = 5000) -> int:
    """Insert records into direct_api_detail table in batches"""
    
    if not records:
        return 0
    
    # Import here to avoid circular dependencies
    import sys
    sys.path.insert(0, '/opt/ai-optimizer')
    from db_save import get_pg_conn
    
    conn = get_pg_conn()
    cur = conn.cursor()
    
    inserted = 0
    total_records = len(records)
    
    print(f"Inserting {total_records:,} records in batches of {batch_size:,}...")
    
    for batch_start in range(0, total_records, batch_size):
        batch_end = min(batch_start + batch_size, total_records)
        batch = records[batch_start:batch_end]
        batch_num = batch_start // batch_size + 1
        total_batches = (total_records + batch_size - 1) // batch_size
        
        # Build multi-value insert
        placeholders = []
        values = []
        param_index = 1
        
        for record in batch:
            placeholders.append(f"""(
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s::jsonb, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )""")
            values.extend([
                record["date"], record["client_login"], record["campaign_id"], record["campaign_type"], record["ad_group_id"],
                record["criterion_id"], record["criterion_type"], record["query"], record["impressions"], record["clicks"],
                record["cost"], record["conversions"], record["device"], record["gender"], record["age"], record["ad_network_type"], record["ad_format"],
                record["placement"], record["income_grade"], record["targeting_category"], record["targeting_location_id"],
                record["avg_click_position"], record["avg_impression_position"], record["slot"], record["avg_traffic_volume"], record["bounces"]
            ])
        
        sql = f"""
        INSERT INTO direct_api_detail (
            date, client_login, campaign_id, campaign_type, ad_group_id,
            criterion_id, criterion_type, query, impressions, clicks, cost,
            conversions, device, gender, age, ad_network_type, ad_format,
            placement, income_grade, targeting_category, targeting_location_id,
            avg_click_position, avg_impression_position, slot, avg_traffic_volume, bounces
        ) VALUES {','.join(placeholders)}
        ON CONFLICT (date, client_login, campaign_id, ad_group_id, criterion_id, device, gender, age, placement, ad_format)
        DO UPDATE SET
            impressions = EXCLUDED.impressions,
            clicks = EXCLUDED.clicks,
            cost = EXCLUDED.cost,
            conversions = EXCLUDED.conversions,
            updated_at = NOW()
        """
        
        try:
            cur.execute(sql, values)
            batch_inserted = cur.rowcount
            inserted += batch_inserted
            print(f"  Batch {batch_num}/{total_batches}: inserted {batch_inserted:,} rows ({batch_start:,}-{batch_end:,})")
        
        except Exception as e:
            print(f"  ❌ Error in batch {batch_num}: {e}")
            conn.rollback()
            cur.close()
            conn.close()
            return inserted
    
    conn.commit()
    cur.close()
    conn.close()
    
    return inserted


def extract_data(mode: str = "daily"):
    """
    Main extraction: fetch and load detailed data WITH conversions
    
    Modes:
    - "daily": Yesterday only (fast)
    - "full": Last 30 days (slow, splits into weekly chunks to avoid API row limits)
    
    Process:
    1. Split date range into chunks (API returns max 500K rows)
    2. Fetch CUSTOM_REPORT for each chunk
    3. Aggregate all data
    4. Parse and save to database
    """
    
    if mode == "daily":
        date_from, date_to = get_yesterday()
        print(f"\n📅 Mode: DAILY (yesterday only)")
    elif mode == "full":
        date_from, date_to = get_last_30_days()
        print(f"\n📅 Mode: FULL (last 30 days, excluding today)")
    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    # For monthly refresh, delete old data first
    if mode == "full":
        print("🗑️  Clearing old direct_api_detail data...")
        try:
            import sys
            sys.path.insert(0, '/opt/ai-optimizer')
            from db_save import get_pg_conn
            conn = get_pg_conn()
            cur = conn.cursor()
            cur.execute("TRUNCATE direct_api_detail CASCADE")
            conn.commit()
            cur.close()
            conn.close()
            print("✅ Old data cleared")
        except Exception as e:
            print(f"⚠️  Could not clear old data: {e}")
    
    print(f"\n{'='*70}")
    print(f"Extracting detailed data: {date_from} to {date_to}")
    print(f"{'='*70}\n")
    
    # Split date range into chunks to avoid API row limit (500K per request)
    date_ranges = split_date_range(date_from, date_to, max_days=7)
    print(f"STEP 1: Fetching CUSTOM_REPORT")
    print(f"        Splitting into {len(date_ranges)} requests (7-day chunks)")
    print(f"        Goals: {len(CONFIG['goal_ids'])} conversion targets")
    print(f"        Attribution Models: {CONFIG['attribution_models']}")
    print("-" * 70)
    
    # Fetch all chunks
    all_dfs = []
    total_rows = 0
    
    for idx, (chunk_from, chunk_to) in enumerate(date_ranges, 1):
        print(f"\n[{idx}/{len(date_ranges)}] Fetching {chunk_from} to {chunk_to}...")
        
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
            report_type="CUSTOM_REPORT",
        )
        
        df, conversion_columns = parse_detailed_report(tsv_data, CONFIG["goal_ids"], "CUSTOM_REPORT")
        
        if df.empty:
            print(f"  ⚠️  No data for this chunk")
        else:
            print(f"  ✅ Loaded {len(df)} rows")
            all_dfs.append(df)
            total_rows += len(df)
    
    if not all_dfs:
        print("❌ No data received from any API call!")
        return 0
    
    # Combine all DataFrames
    print(f"\n✅ Combining {len(all_dfs)} chunks...")
    df = pd.concat(all_dfs, ignore_index=True)
    print(f"   Total rows: {len(df)}")
    
    # Check for conversions in response
    conv_cols = [col for col in df.columns if col.startswith('Conversions_')]
    if conv_cols:
        print(f"   Conversions columns found: {len(conv_cols)}")
    
    # ========== STEP 2: Parse and save ==========
    print("\nSTEP 2: Converting to database records and inserting")
    print("-" * 70)
    
    # Build conversion_data dict (needed for aggregation)
    conversion_data = {}
    for goal_id in CONFIG["goal_ids"]:
        conversion_data[goal_id] = {}
        for model in CONFIG["attribution_models"]:
            col = f"Conversions_{goal_id}_{model}"
            if col in df.columns:
                conversion_data[goal_id][model] = col
    
    # Convert to records (with aggregation for duplicate keys)
    records = df_to_api_detail_records(df, conversion_data)
    print(f"Prepared {len(records)} unique records (after deduplication/aggregation)")
    
    inserted_total = insert_api_detail_records(records)
    print(f"✅ Inserted {inserted_total} rows into direct_api_detail\n")
    
    print(f"{'='*70}")
    print(f"✅ COMPLETED: {inserted_total} total rows in direct_api_detail")
    print(f"{'='*70}\n")
    
    return inserted_total


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    extract_data(mode=mode)

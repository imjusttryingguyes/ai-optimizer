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
    """Get date range for last 30 days"""
    today = datetime.now().date()
    date_from = today - timedelta(days=30)
    return date_from.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def get_yesterday():
    """Get date range for yesterday only"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")


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
    Convert DataFrame rows to direct_api_detail table records
    
    Returns list of dicts ready for INSERT (with deduplication)
    """
    
    records = []
    seen_keys = set()  # For deduplication
    
    for _, row in df.iterrows():
        # Build conversions JSONB
        conversions_json = {}
        for goal_id, models in conversion_data.items():
            goal_conversions = {}
            for model, col in models.items():
                if col in row.index:
                    conv_val = row[col]
                    if pd.notna(conv_val) and conv_val > 0:
                        goal_conversions[model] = int(conv_val)
            if goal_conversions:
                conversions_json[str(goal_id)] = goal_conversions
        
        # Handle NaN/None/dashes values
        def get_val(key, default=None, as_int=False, as_float=False):
            val = row.get(key)
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
        
        date = get_val("Date")
        client_login = get_val("ClientLogin")
        campaign_id = get_val("CampaignId", as_int=True)
        ad_group_id = get_val("AdGroupId", as_int=True)
        criterion_id = get_val("CriterionId", as_int=True)
        device = get_val("Device")
        gender = get_val("Gender")
        age = get_val("Age")
        placement = get_val("Placement")
        ad_format = get_val("AdFormat")
        
        # Create dedup key (same as UNIQUE constraint)
        dedup_key = (date, client_login, campaign_id, ad_group_id, criterion_id, device, gender, age, placement, ad_format)
        
        if dedup_key in seen_keys:
            continue  # Skip duplicate
        
        seen_keys.add(dedup_key)
        
        record = {
            "date": date,
            "client_login": client_login,
            
            # Campaign
            "campaign_id": campaign_id,
            "campaign_type": get_val("CampaignType"),
            "ad_group_id": ad_group_id,
            
            # Criteria
            "criterion_id": criterion_id,
            "criterion_type": get_val("CriterionType"),
            "query": get_val("Query"),
            
            # Metrics
            "impressions": get_val("Impressions", default=0, as_int=True),
            "clicks": get_val("Clicks", default=0, as_int=True),
            "cost": float(get_val("cost_rub", default=0)),
            
            # Conversions
            "conversions": json.dumps(conversions_json) if conversions_json else "{}",
            
            # Dimensions
            "device": device,
            "gender": gender,
            "age": age,
            
            # Placement
            "ad_network_type": get_val("AdNetworkType"),
            "ad_format": ad_format,
            "placement": placement,
            "income_grade": get_val("IncomeGrade"),
            
            # Targeting
            "targeting_category": get_val("TargetingCategory"),
            "targeting_location_id": get_val("TargetingLocationId", as_int=True),
            
            # Position (handle dashes)
            "avg_click_position": get_val("AvgClickPosition", as_float=True),
            "avg_impression_position": get_val("AvgImpressionPosition", as_float=True),
            "slot": get_val("Slot"),
            "avg_traffic_volume": get_val("AvgTrafficVolume", as_int=True),
            "bounces": get_val("Bounces", as_int=True),
        }
        
        records.append(record)
    
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
    Main extraction: fetch and load detailed data
    
    Modes:
    - "daily": Yesterday only (fast, ~30 sec)
    - "full": Last 30 days (slow, ~5-10 min, used monthly)
    """
    
    if mode == "daily":
        date_from, date_to = get_yesterday()
        print(f"\n📅 Mode: DAILY (yesterday only)")
    elif mode == "full":
        date_from, date_to = get_last_30_days()
        print(f"\n📅 Mode: FULL (last 30 days)")
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
    
    print(f"\n{'='*60}")
    print(f"Extracting detailed data: {date_from} to {date_to}")
    print(f"{'='*60}\n")
    
    # Step 1: Fetch CUSTOM_REPORT (all dimensions except Query)
    print("STEP 1: Fetching CUSTOM_REPORT (device, age, gender, placement, etc.)")
    print("-" * 60)
    
    tsv_content = fetch_detailed_report(
        token=CONFIG["token"],
        client_login=CONFIG["client_login"],
        date_from=date_from,
        date_to=date_to,
        goal_ids=CONFIG["goal_ids"],
        attribution_models=CONFIG["attribution_models"],
        use_sandbox=CONFIG["use_sandbox"],
        max_retries=CONFIG["max_retries"],
        retry_sleep_seconds=CONFIG["retry_sleep_seconds"],
        report_type="CUSTOM_REPORT",
    )
    
    # Parse report
    df_custom, conversion_data = parse_detailed_report(tsv_content, CONFIG["goal_ids"], "CUSTOM_REPORT")
    
    if df_custom.empty:
        print("No data in CUSTOM_REPORT!")
        inserted_total = 0
    else:
        # Convert to records and insert
        records = df_to_api_detail_records(df_custom, conversion_data)
        print(f"Prepared {len(records)} records for insertion")
        inserted_total = insert_api_detail_records(records)
        print(f"✅ Inserted {inserted_total} rows into direct_api_detail\n")
    
    print(f"{'='*60}")
    print(f"✅ COMPLETED: {inserted_total} total rows in direct_api_detail")
    print(f"{'='*60}\n")
    
    return inserted_total


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    extract_data(mode=mode)

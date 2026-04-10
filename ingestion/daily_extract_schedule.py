#!/usr/bin/env python3
"""
Daily Extraction Scheduler for Yandex Direct API

Runs nightly to:
1. Extract last 30 days of detailed data
2. Update direct_api_detail table (upsert)
3. Rebuild kpi_daily_summary aggregates
4. Optionally send Telegram notification
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/ai-optimizer/logs/daily_extract.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_extraction(mode: str = "daily"):
    """Execute the extraction with specified mode"""
    
    logger.info("="*70)
    logger.info(f"Starting Extraction (Mode: {mode.upper()})")
    logger.info("="*70)
    
    try:
        # Import extraction module
        sys.path.insert(0, '/opt/ai-optimizer')
        from ingestion.yandex_detailed_extract import extract_data
        
        # Run extraction
        inserted = extract_data(mode=mode)
        logger.info(f"Extraction completed (mode={mode}): {inserted} rows inserted")
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        return False
    
    return True


def rebuild_kpi_summary():
    """Rebuild KPI daily summary from detail data"""
    
    logger.info("-"*70)
    logger.info("Rebuilding KPI Daily Summary")
    logger.info("-"*70)
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        
        cur = conn.cursor()
        
        # Truncate and repopulate
        cur.execute("TRUNCATE kpi_daily_summary")
        
        cur.execute("""
        INSERT INTO kpi_daily_summary (
            account_id, date, impressions, clicks, spend_rub, conversions, detail_rows
        )
        SELECT 
            d.client_login as account_id,
            d.date,
            SUM(d.impressions)::bigint as impressions,
            SUM(d.clicks)::bigint as clicks,
            SUM(d.cost) as spend_rub,
            0 as conversions,
            COUNT(*)::bigint as detail_rows
        FROM direct_api_detail d
        GROUP BY d.date, d.client_login
        """)
        
        conn.commit()
        
        # Log summary
        cur.execute("""
        SELECT 
            COUNT(*) as days,
            SUM(clicks) as total_clicks,
            SUM(impressions) as total_impressions,
            SUM(spend_rub) as total_spend
        FROM kpi_daily_summary
        """)
        
        days, clicks, impr, spend = cur.fetchone()
        logger.info(f"✅ KPI Summary updated: {days} days, {clicks:,} clicks, {spend:,.2f} ₽")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"KPI summary rebuild failed: {e}", exc_info=True)
        return False
    
    return True


def main():
    """Main execution"""
    
    mode = os.getenv('EXTRACT_MODE', 'daily')  # Can be 'daily' or 'full'
    
    logger.info(f"Daily extraction started at {datetime.now()} (mode={mode})")
    
    # Step 1: Extract data
    if not run_extraction(mode=mode):
        logger.error("Extraction failed, aborting")
        return 1
    
    # Step 2: Rebuild KPI summary
    if not rebuild_kpi_summary():
        logger.error("KPI summary rebuild failed")
        return 1
    
    logger.info("="*70)
    logger.info(f"✅ Extraction completed successfully (mode={mode})")
    logger.info("="*70)
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

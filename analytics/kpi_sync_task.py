"""
Daily KPI sync task - runs nightly to fetch conversions and update KPI metrics
Uses APScheduler for background task scheduling
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os

from analytics.yandex_api import YandexDirectAPIClient
from analytics.kpi_engine import KPICalculationEngine
from analytics.telegram_notifier import TelegramNotifier

logger = logging.getLogger(__name__)


class KPIDailySync:
    """Handle daily KPI data synchronization"""
    
    def __init__(self, db_connection, yandex_token: str, telegram_token: str = None):
        """
        Initialize daily sync task
        
        Args:
            db_connection: psycopg2 database connection
            yandex_token: Yandex Direct API token
            telegram_token: Telegram bot token (optional)
        """
        self.conn = db_connection
        self.yandex = YandexDirectAPIClient(yandex_token)
        self.kpi_engine = KPICalculationEngine(db_connection)
        self.telegram = TelegramNotifier(telegram_token) if telegram_token else None
        
        self.execution_log = []
    
    def sync_all_accounts(self) -> dict:
        """
        Sync data for all active accounts
        
        Returns:
            Summary dict with results
        """
        logger.info("Starting daily KPI sync for all accounts")
        self.execution_log = []
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "accounts_processed": 0,
            "accounts_failed": 0,
            "errors": []
        }
        
        try:
            # Get all accounts with active KPI plans
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT DISTINCT account_id 
                FROM kpi_monthly_plan
                WHERE EXTRACT(YEAR FROM year_month) = EXTRACT(YEAR FROM NOW())
                AND EXTRACT(MONTH FROM year_month) = EXTRACT(MONTH FROM NOW())
                ORDER BY account_id
            """)
            
            accounts = cur.fetchall()
            cur.close()
            
            if not accounts:
                logger.warning("No active accounts found for KPI sync")
                results["status"] = "warning"
                results["errors"].append("No active accounts found")
                return results
            
            # Sync each account
            for row in accounts:
                account_id = row["account_id"]
                try:
                    self._sync_account(account_id)
                    results["accounts_processed"] += 1
                    self._log(f"✅ Account {account_id} synced successfully")
                    
                except Exception as e:
                    results["accounts_failed"] += 1
                    error_msg = f"Failed to sync {account_id}: {str(e)}"
                    results["errors"].append(error_msg)
                    self._log(f"❌ {error_msg}")
                    logger.error(error_msg)
            
            # Overall status
            if results["accounts_failed"] > 0:
                results["status"] = "partial"
            
            # Save execution log
            self._save_execution_log(results)
            logger.info(f"Daily sync complete: {results['accounts_processed']} succeeded, "
                       f"{results['accounts_failed']} failed")
            
            return results
            
        except Exception as e:
            logger.error(f"Fatal error in daily sync: {e}")
            results["status"] = "failed"
            results["errors"].append(str(e))
            return results
    
    def _sync_account(self, account_id: str):
        """
        Sync single account
        
        Args:
            account_id: Account ID to sync
        """
        yesterday = date.today() - timedelta(days=1)
        
        # Fetch data from Yandex API
        self._log(f"Fetching data for {account_id} from Yandex API...")
        stats = self.yandex.get_daily_stats(yesterday, account_id)
        
        if not stats:
            self._log(f"No data returned from API for {account_id} on {yesterday}")
            return
        
        # Update kpi_daily_summary
        self._update_daily_summary(account_id, yesterday, stats)
        self._log(f"Updated kpi_daily_summary for {account_id}")
        
        # Recalculate 30-day rolling baseline
        self._recalculate_segment_baseline(account_id)
        self._log(f"Recalculated segment_baseline for {account_id}")
        
        # Check if should send Telegram alert (deviation > ±10%)
        if self.telegram:
            self._send_telegram_alert_if_needed(account_id)
    
    def _update_daily_summary(self, account_id: str, day: date, stats: dict):
        """
        Update kpi_daily_summary table with latest data
        
        Args:
            account_id: Account ID
            day: Date
            stats: Stats dict from Yandex API
        """
        cur = self.conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO kpi_daily_summary 
                (account_id, date, spend_rub, clicks, conversions, 
                 impressions, ctr, cpc, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (account_id, date) DO UPDATE SET
                    spend_rub = EXCLUDED.spend_rub,
                    clicks = EXCLUDED.clicks,
                    conversions = EXCLUDED.conversions,
                    impressions = EXCLUDED.impressions,
                    ctr = EXCLUDED.ctr,
                    cpc = EXCLUDED.cpc,
                    updated_at = NOW()
            """, (
                account_id,
                day,
                stats.get("spend_rub", 0),
                stats.get("clicks", 0),
                stats.get("conversions", 0),
                stats.get("impressions", 0),
                stats.get("ctr", 0),
                stats.get("cpc", 0)
            ))
            
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cur.close()
    
    def _recalculate_segment_baseline(self, account_id: str):
        """
        Recalculate 30-day rolling baseline for all segments
        
        Args:
            account_id: Account ID
        """
        cur = self.conn.cursor()
        
        try:
            # Delete old baseline for this account
            cur.execute("DELETE FROM segment_baseline WHERE account_id = %s", (account_id,))
            
            # Recalculate from raw data (last 30 days)
            cur.execute("""
                WITH segment_data AS (
                    SELECT 
                        account_id,
                        CASE 
                            WHEN device_category = 'desktop' THEN 'device_desktop'
                            WHEN device_category = 'mobile' THEN 'device_mobile'
                            WHEN device_category = 'tablet' THEN 'device_tablet'
                            ELSE 'device_unknown'
                        END as segment_type,
                        SUM(spend_rub) as total_spend,
                        SUM(clicks) as total_clicks,
                        COUNT(DISTINCT date) as days,
                        AVG(clicks::NUMERIC) FILTER (WHERE clicks > 0) as avg_daily_clicks
                    FROM direct_daily_fact
                    WHERE account_id = %s
                    AND date >= NOW()::DATE - INTERVAL '30 days'
                    GROUP BY account_id, segment_type
                )
                INSERT INTO segment_baseline 
                (account_id, segment_type, period_days, 
                 total_spend, total_clicks, avg_cpc, avg_daily_volume, last_updated)
                SELECT 
                    account_id,
                    segment_type,
                    30,
                    total_spend,
                    total_clicks,
                    CASE WHEN total_clicks > 0 THEN total_spend / total_clicks ELSE 0 END,
                    avg_daily_clicks,
                    NOW()
                FROM segment_data
            """, (account_id,))
            
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cur.close()
    
    def _send_telegram_alert_if_needed(self, account_id: str):
        """
        Send Telegram alert if KPI deviation exceeds threshold
        
        Args:
            account_id: Account ID
        """
        try:
            # Get KPI status
            kpi_status = self.kpi_engine.calculate_kpi_status(account_id)
            
            if "error" in kpi_status:
                self._log(f"Skipping Telegram for {account_id}: {kpi_status['error']}")
                return
            
            # Check deviation thresholds
            budget_dev = abs(kpi_status["budget"]["pacing_pct"] - 100)
            conversions_dev = abs(kpi_status["conversions"]["pacing_pct"] - 100)
            cpa_dev = abs(kpi_status["cpa"]["deviation_pct"])
            
            # Send if any metric deviates > 10%
            if budget_dev > 10 or conversions_dev > 10 or cpa_dev > 10:
                chat_id = os.getenv(f"TELEGRAM_CHAT_ID_{account_id}") or os.getenv("TELEGRAM_CHAT_ID")
                
                if chat_id:
                    dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:5000")
                    success = self.telegram.send_kpi_report(
                        chat_id, 
                        kpi_status,
                        f"{dashboard_url}/kpi"
                    )
                    
                    if success:
                        self._log(f"📱 Telegram alert sent for {account_id}")
                    else:
                        self._log(f"⚠️ Failed to send Telegram for {account_id}")
                else:
                    self._log(f"⚠️ No Telegram chat_id for {account_id}")
            else:
                self._log(f"No alert needed for {account_id} (all metrics within ±10%)")
        
        except Exception as e:
            self._log(f"❌ Error sending Telegram: {str(e)}")
            logger.error(f"Telegram alert error: {e}")
    
    def _save_execution_log(self, summary: dict):
        """
        Save execution log to database
        
        Args:
            summary: Execution summary
        """
        cur = self.conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO kpi_sync_log 
                (executed_at, accounts_processed, accounts_failed, status, details)
                VALUES (NOW(), %s, %s, %s, %s)
            """, (
                summary["accounts_processed"],
                summary["accounts_failed"],
                summary["status"],
                "\n".join(self.execution_log)
            ))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to save execution log: {e}")
            self.conn.rollback()
        finally:
            cur.close()
    
    def _log(self, message: str):
        """Add message to execution log"""
        self.execution_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        logger.info(message)


def create_kpi_sync_task(db_connection, yandex_token: str, 
                        telegram_token: str = None) -> KPIDailySync:
    """Factory function to create KPI sync task"""
    return KPIDailySync(db_connection, yandex_token, telegram_token)

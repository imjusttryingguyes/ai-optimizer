"""
KPI Calculation Engine - Real-time pacing metrics for Level 1 Dashboard
"""

import psycopg2
from datetime import datetime, date, timedelta
from typing import Dict, Optional, Tuple
import calendar
import logging

logger = logging.getLogger(__name__)


class KPICalculationEngine:
    """Calculate KPI pacing metrics for dashboard"""
    
    def __init__(self, db_connection):
        """
        Initialize KPI engine
        
        Args:
            db_connection: psycopg2 connection to database
        """
        self.conn = db_connection
        self.cur = None
    
    def _get_cursor(self):
        """Get database cursor"""
        if self.cur is None or self.cur.closed:
            self.cur = self.conn.cursor()
        return self.cur
    
    def get_current_month_plan(self, account_id: str) -> Optional[Dict]:
        """
        Get KPI plan for current month
        
        Args:
            account_id: Account ID
            
        Returns:
            Dict with plan data or None if not found
        """
        cur = self._get_cursor()
        
        current_month = datetime.now().replace(day=1).date()
        
        cur.execute("""
            SELECT 
                id, account_id, year_month, month_start, month_end,
                budget_rub, leads_target, cpa_target_rub, roi_target
            FROM kpi_monthly_plan
            WHERE account_id = %s 
            AND EXTRACT(MONTH FROM year_month) = EXTRACT(MONTH FROM %s)
            AND EXTRACT(YEAR FROM year_month) = EXTRACT(YEAR FROM %s)
            LIMIT 1
        """, (account_id, current_month, current_month))
        
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "account_id": row[1],
                "year_month": row[2],
                "month_start": row[3],
                "month_end": row[4],
                "budget_rub": float(row[5]),
                "leads_target": float(row[6]),
                "cpa_target_rub": float(row[7]),
                "roi_target": float(row[8]) if row[8] else None
            }
        return None
    
    def get_month_actual_metrics(self, account_id: str, month_date: Optional[date] = None) -> Dict:
        """
        Get actual metrics for current/specified month to date
        
        Args:
            account_id: Account ID
            month_date: Date to use as reference (default: today)
            
        Returns:
            Dict with actual metrics
        """
        if month_date is None:
            month_date = date.today()
        
        month_start = month_date.replace(day=1)
        month_end = date(month_date.year, month_date.month, 
                        calendar.monthrange(month_date.year, month_date.month)[1])
        
        cur = self._get_cursor()
        
        # Get spend and impressions from kpi_daily_summary for current month
        cur.execute("""
            SELECT 
                SUM(spend_rub)::NUMERIC as total_spend,
                SUM(impressions)::BIGINT as total_impressions,
                COUNT(DISTINCT date) as days_data
            FROM kpi_daily_summary
            WHERE account_id = %s
            AND date >= %s
            AND date <= %s
        """, (account_id, month_start, month_date))
        
        row = cur.fetchone()
        total_spend = float(row[0]) if row[0] else 0
        total_impressions = int(row[1]) if row[1] else 0
        days_with_data = int(row[2]) if row[2] else 0
        
        # If no data for current month, try last 30 days
        if days_with_data == 0:
            thirty_days_ago = month_date - timedelta(days=30)
            cur.execute("""
                SELECT 
                    SUM(spend_rub)::NUMERIC as total_spend,
                    SUM(impressions)::BIGINT as total_impressions,
                    COUNT(DISTINCT date) as days_data,
                    MIN(date) as actual_start,
                    MAX(date) as actual_end
                FROM kpi_daily_summary
                WHERE account_id = %s
                AND date >= %s
                AND date <= %s
            """, (account_id, thirty_days_ago, month_date))
            
            row = cur.fetchone()
            if row[2] > 0:  # Has data in last 30 days
                total_spend = float(row[0]) if row[0] else 0
                total_impressions = int(row[1]) if row[1] else 0
                days_with_data = int(row[2]) if row[2] else 0
                # Update date range to actual data range
                month_start = row[3]
                month_end = row[4]
        
        # Get conversions from direct_api_detail
        # Note: Yandex API currently returns empty {} for conversions field, so conversions = 0
        # TODO: When API provides conversion data, update this query
        total_conversions = 0
        
        return {
            "month_start": month_start,
            "month_end": month_end,
            "period_end": month_date,
            "total_spend": total_spend,
            "total_conversions": total_conversions,
            "total_impressions": total_impressions,
            "days_with_data": days_with_data
        }
    
    def calculate_kpi_status(self, account_id: str) -> Dict:
        """
        Calculate comprehensive KPI status for dashboard
        
        Args:
            account_id: Account ID
            
        Returns:
            Dict with all KPI metrics:
            {
                "plan": {...},
                "actual": {...},
                "budget": {...},
                "leads": {...},
                "cpa": {...},
                "forecast": {...},
                "status": {...}
            }
        """
        today = date.today()
        
        # Get plan
        plan = self.get_current_month_plan(account_id)
        if not plan:
            return {"error": f"No KPI plan found for {account_id} in current month"}
        
        # Get actual
        actual = self.get_month_actual_metrics(account_id, today)
        
        # Calculate days
        total_days = (plan["month_end"] - plan["month_start"]).days + 1
        days_elapsed = (today - plan["month_start"]).days + 1
        days_remaining = (plan["month_end"] - today).days
        
        # Budget metrics
        daily_budget_pace = plan["budget_rub"] / total_days
        budget_should_spend = daily_budget_pace * days_elapsed
        budget_pacing_pct = (actual["total_spend"] / budget_should_spend * 100) if budget_should_spend > 0 else 0
        
        # Leads/conversions metrics
        daily_leads_pace = plan["leads_target"] / total_days
        leads_should_get = daily_leads_pace * days_elapsed
        leads_pacing_pct = (actual["total_conversions"] / leads_should_get * 100) if leads_should_get > 0 else 0
        
        # CPA metrics
        avg_cpa_actual = (actual["total_spend"] / actual["total_conversions"]) if actual["total_conversions"] > 0 else 0
        cpa_deviation_pct = ((avg_cpa_actual - plan["cpa_target_rub"]) / plan["cpa_target_rub"] * 100) if plan["cpa_target_rub"] > 0 else 0
        
        # Forecast
        if days_elapsed > 0 and actual["total_spend"] > 0:
            forecast_spend = (actual["total_spend"] / days_elapsed) * total_days
            forecast_conversions = (actual["total_conversions"] / days_elapsed) * total_days
            forecast_cpa = (forecast_spend / forecast_conversions) if forecast_conversions > 0 else 0
        else:
            forecast_spend = plan["budget_rub"]
            forecast_conversions = plan["leads_target"]
            forecast_cpa = plan["cpa_target_rub"]
        
        # Status determination
        def get_status(pacing_pct: float) -> str:
            """Determine status based on pacing percentage"""
            if pacing_pct > 110:
                return "ahead"
            elif pacing_pct < 90:
                return "behind"
            return "on_track"
        
        def get_severity(pacing_pct: float) -> str:
            """Determine severity indicator"""
            if pacing_pct > 120 or pacing_pct < 80:
                return "critical"
            elif pacing_pct > 110 or pacing_pct < 90:
                return "warning"
            return "ok"
        
        return {
            "account_id": account_id,
            "as_of_date": today.isoformat(),
            "plan": plan,
            "actual": actual,
            "pacing": {
                "total_days": total_days,
                "days_elapsed": days_elapsed,
                "days_remaining": days_remaining,
                "pct_month_complete": round((days_elapsed / total_days * 100), 1)
            },
            "budget": {
                "target": plan["budget_rub"],
                "spent": round(actual["total_spend"], 2),
                "should_spend": round(budget_should_spend, 2),
                "remaining": round(plan["budget_rub"] - actual["total_spend"], 2),
                "pacing_pct": round(budget_pacing_pct, 1),
                "daily_pace": round(daily_budget_pace, 2),
                "status": get_status(budget_pacing_pct),
                "severity": get_severity(budget_pacing_pct)
            },
            "conversions": {
                "target": plan["leads_target"],
                "actual": actual["total_conversions"],
                "should_get": round(leads_should_get, 1),
                "remaining": max(0, plan["leads_target"] - actual["total_conversions"]),
                "pacing_pct": round(leads_pacing_pct, 1),
                "daily_pace": round(daily_leads_pace, 2),
                "status": get_status(leads_pacing_pct),
                "severity": get_severity(leads_pacing_pct)
            },
            "cpa": {
                "target": plan["cpa_target_rub"],
                "actual": round(avg_cpa_actual, 2),
                "deviation_pct": round(cpa_deviation_pct, 1),
                "status": "critical" if abs(cpa_deviation_pct) > 20 else ("warning" if abs(cpa_deviation_pct) > 10 else "ok")
            },
            "forecast": {
                "end_month_spend": round(forecast_spend, 2),
                "end_month_conversions": int(forecast_conversions),
                "end_month_cpa": round(forecast_cpa, 2),
                "budget_variance": round(forecast_spend - plan["budget_rub"], 2),
                "leads_variance": int(forecast_conversions - plan["leads_target"]),
                "cpa_variance": round(forecast_cpa - plan["cpa_target_rub"], 2)
            },
            "summary": {
                "overall_status": "critical" if (
                    get_severity(budget_pacing_pct) == "critical" or 
                    get_severity(leads_pacing_pct) == "critical"
                ) else ("warning" if (
                    get_severity(budget_pacing_pct) == "warning" or 
                    get_severity(leads_pacing_pct) == "warning"
                ) else "ok"),
                "key_alerts": self._generate_alerts(
                    budget_pacing_pct, leads_pacing_pct, cpa_deviation_pct
                )
            }
        }
    
    @staticmethod
    def _generate_alerts(budget_pacing: float, leads_pacing: float, cpa_dev: float) -> list:
        """Generate alert messages"""
        alerts = []
        
        if budget_pacing > 110:
            alerts.append(f"Budget pacing +{budget_pacing-100:.0f}% - spending ahead of plan")
        elif budget_pacing < 90:
            alerts.append(f"Budget pacing {budget_pacing:.0f}% - underutilizing budget")
        
        if leads_pacing > 110:
            alerts.append(f"Leads pacing +{leads_pacing-100:.0f}% - exceeding target")
        elif leads_pacing < 90:
            alerts.append(f"Leads pacing {leads_pacing:.0f}% - behind target leads")
        
        if cpa_dev > 20:
            alerts.append(f"CPA +{cpa_dev:.0f}% above target - review campaign efficiency")
        elif cpa_dev < -20:
            alerts.append(f"CPA {cpa_dev:.0f}% below target - strong performance")
        
        return alerts
    
    def close(self):
        """Close database connection"""
        if self.cur and not self.cur.closed:
            self.cur.close()


def create_kpi_engine(connection) -> KPICalculationEngine:
    """Factory function to create KPI engine"""
    return KPICalculationEngine(connection)

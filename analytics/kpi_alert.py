"""
KPI Account Health Monitoring.
Detects when accounts deviate from plan (CPA, leads/day).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .analyzer_base import Analyzer


class KPIAlertAnalyzer(Analyzer):
    """Monitor account KPI against plan thresholds."""

    def analyze(self) -> list:
        """Check account KPIs vs plan and generate alerts."""
        query = """
            SELECT
                account_id,
                client_login,
                cpa_plan,
                conversions_plan_daily,
                spend_rub_week,
                conversions_week,
                data_days_week,
                cpa_week,
                conversions_per_day_week,
                cpa_30d,
                conversions_per_day_30d
            FROM kpi_account_vs_plan
            WHERE account_id IS NOT NULL
            ORDER BY account_id
        """
        
        rows = self.execute_query(query)
        
        for r in rows:
            (
                account_id,
                client_login,
                cpa_plan,
                conv_plan_daily,
                spend_week,
                conv_week,
                data_days_week,
                cpa_week,
                conv_week_per_day,
                cpa_30d,
                conv_30d_per_day,
            ) = r

            coverage_note = f"(данных дней: {int(data_days_week)})"
            
            alerts = []
            if cpa_week is not None and float(cpa_week) > float(cpa_plan):
                alerts.append(("CPA_BAD", "CPA выше плана", float(cpa_week) - float(cpa_plan)))
            if float(conv_week_per_day) < float(conv_plan_daily):
                alerts.append(("LEADS_BAD", "Лидов/день ниже плана", 
                              (float(conv_plan_daily) - float(conv_week_per_day)) * 100))

            for alert_type, desc, diff in alerts:
                self.add_insight(
                    account_id=str(account_id),
                    type=f"ACCOUNT_KPI_{alert_type}",
                    entity_type="account",
                    entity_id=str(account_id),
                    severity=min(abs(diff) / (float(cpa_plan) if 'CPA' in alert_type else float(conv_plan_daily)), 1.0),
                    impact_rub=spend_week if spend_week else 0,
                    title=f"Аккаунт {account_id}: {desc}",
                    description=f"{coverage_note}\nCPA: неделя={self.fmt_num(cpa_week)} план={self.fmt_num(cpa_plan)}\nЛидов/день: неделя={self.fmt_num(conv_week_per_day)} план={self.fmt_num(conv_plan_daily)}",
                    recommendation=f"Проверить кампании аккаунта {account_id}",
                    evidence={
                        "cpa_week": float(cpa_week) if cpa_week else None,
                        "cpa_plan": float(cpa_plan),
                        "conv_per_day_week": float(conv_week_per_day),
                        "conv_per_day_plan": float(conv_plan_daily),
                        "data_days": int(data_days_week),
                    },
                    confidence=0.95 if data_days_week >= 6 else 0.7,
                )

        return self.insights


def main():
    """Run KPI alert analysis."""
    analyzer = KPIAlertAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()

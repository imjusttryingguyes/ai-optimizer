"""
Account-level trend analysis.
Detects when CPA or leads/day are trending up or down significantly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .analyzer_base import Analyzer


class TrendAnalyzer(Analyzer):
    """Analyze trends in account KPI (CPA and leads/day)."""

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.thresholds = {
            'min_data_days_last': 2,
            'min_data_days_prev': 3,
            'cpa_bad_threshold': 1.3,
            'cpa_good_threshold': 0.7,
            'leads_bad_threshold': 0.7,
            'leads_good_threshold': 1.5,
        }
        self.thresholds.update(self.config.get('thresholds', {}))

    def analyze(self) -> list:
        """Run trend analysis."""
        query = """
            SELECT
                t.account_id,
                t.anchor_date,
                t.data_days_last_3d,
                t.data_days_prev_4d,
                t.cpa_last_3d,
                t.cpa_prev_4d,
                t.conv_per_day_last_3d,
                t.conv_per_day_prev_4d,
                COALESCE(at.cpa_plan, 0) AS cpa_plan
            FROM kpi_account_trends t
            LEFT JOIN account_targets at
                ON at.account_id = t.account_id
            WHERE at.is_active = true
        """
        
        rows = self.execute_query(query)
        
        for (
            account_id,
            anchor_date,
            data_days_last_3d,
            data_days_prev_4d,
            cpa_last,
            cpa_prev,
            conv_last,
            conv_prev,
            cpa_plan
        ) in rows:
            cpa_last = float(cpa_last or 0)
            cpa_prev = float(cpa_prev or 0)
            conv_last = float(conv_last or 0)
            conv_prev = float(conv_prev or 0)
            cpa_plan = float(cpa_plan or 0)

            data_days_last_3d = int(data_days_last_3d or 0)
            data_days_prev_4d = int(data_days_prev_4d or 0)

            # Skip if insufficient data
            if data_days_last_3d < self.thresholds['min_data_days_last'] or data_days_prev_4d < self.thresholds['min_data_days_prev']:
                continue

            # CPA worsened
            if cpa_prev > 0 and cpa_last > cpa_prev * self.thresholds['cpa_bad_threshold']:
                change_pct = ((cpa_last - cpa_prev) / cpa_prev) * 100
                self.add_insight(
                    account_id=str(account_id),
                    type="ACCOUNT_CPA_TREND_BAD",
                    entity_type="account",
                    entity_id=str(account_id),
                    severity=0.8,
                    impact_rub=max(0.0, cpa_last - cpa_prev),
                    title=f"CPA ухудшилась на {change_pct:.0f}%",
                    description=f"CPA за 3 дня: {self.fmt_num(cpa_last)}, за предыдущие 4 дня: {self.fmt_num(cpa_prev)}",
                    recommendation="Проверить кампании, сегменты и плейсменты",
                    evidence={
                        "cpa_last_3d": cpa_last,
                        "cpa_prev_4d": cpa_prev,
                        "change_pct": change_pct,
                    },
                    confidence=0.95,
                )

            # CPA improved
            if cpa_prev > 0 and cpa_last < cpa_prev * self.thresholds['cpa_good_threshold']:
                change_pct = ((cpa_prev - cpa_last) / cpa_prev) * 100
                saved_rub = max(0.0, (cpa_prev - cpa_last) * conv_last * 3)
                self.add_insight(
                    account_id=str(account_id),
                    type="ACCOUNT_CPA_TREND_GOOD",
                    entity_type="account",
                    entity_id=str(account_id),
                    severity=0.55,
                    impact_rub=saved_rub,
                    title=f"CPA улучшилась на {change_pct:.0f}%",
                    description=f"CPA за 3 дня: {self.fmt_num(cpa_last)}, за предыдущие 4 дня: {self.fmt_num(cpa_prev)}",
                    recommendation="Продолжить текущую стратегию и увеличить масштаб успешных кампаний",
                    evidence={
                        "cpa_last_3d": cpa_last,
                        "cpa_prev_4d": cpa_prev,
                        "change_pct": change_pct,
                    },
                    confidence=0.95,
                )

            # Leads dropped
            if conv_prev > 0 and conv_last < conv_prev * self.thresholds['leads_bad_threshold']:
                change_pct = ((conv_prev - conv_last) / conv_prev) * 100
                lost_leads = max(0.0, conv_prev - conv_last)
                impact = lost_leads * cpa_plan
                self.add_insight(
                    account_id=str(account_id),
                    type="ACCOUNT_LEADS_TREND_BAD",
                    entity_type="account",
                    entity_id=str(account_id),
                    severity=0.75,
                    impact_rub=impact,
                    title=f"Лиды/день упали на {change_pct:.0f}%",
                    description=f"Лиды за 3 дня: {self.fmt_num(conv_last)}, за предыдущие 4 дня: {self.fmt_num(conv_prev)}, потеря: {self.fmt_num(lost_leads)}/день",
                    recommendation="Проверить бюджеты, ставки и доставку кампаний",
                    evidence={
                        "conv_per_day_last_3d": conv_last,
                        "conv_per_day_prev_4d": conv_prev,
                        "lost_leads_per_day": lost_leads,
                        "change_pct": change_pct,
                    },
                    confidence=0.95,
                )

            # Leads increased
            if conv_prev > 0 and conv_last > conv_prev * self.thresholds['leads_good_threshold']:
                change_pct = ((conv_last - conv_prev) / conv_prev) * 100
                added_leads = max(0.0, conv_last - conv_prev)
                impact = added_leads * cpa_plan
                self.add_insight(
                    account_id=str(account_id),
                    type="ACCOUNT_LEADS_TREND_GOOD",
                    entity_type="account",
                    entity_id=str(account_id),
                    severity=0.5,
                    impact_rub=impact,
                    title=f"Лиды/день выросли на {change_pct:.0f}%",
                    description=f"Лиды за 3 дня: {self.fmt_num(conv_last)}, за предыдущие 4 дня: {self.fmt_num(conv_prev)}, прирост: {self.fmt_num(added_leads)}/день",
                    recommendation="Продолжить успешные стратегии и рассмотреть увеличение бюджета",
                    evidence={
                        "conv_per_day_last_3d": conv_last,
                        "conv_per_day_prev_4d": conv_prev,
                        "added_leads_per_day": added_leads,
                        "change_pct": change_pct,
                    },
                    confidence=0.95,
                )

        return self.insights


def main():
    """Run trend analysis."""
    analyzer = TrendAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()

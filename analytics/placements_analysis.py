"""
RSYA Placements analysis.
Identifies placements with waste, poor CR, and great performance.
Uses Wilson score intervals for statistically sound CR comparisons.
"""

import math
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .analyzer_base import Analyzer


def wilson_interval(successes: float, trials: float, z: float = 1.96):
    """Wilson score interval for binomial proportion confidence."""
    if trials <= 0:
        return (0.0, 0.0)
    p = successes / trials
    den = 1.0 + (z * z) / trials
    center = (p + (z * z) / (2.0 * trials)) / den
    half = (z / den) * math.sqrt((p * (1.0 - p) / trials) + (z * z) / (4.0 * trials * trials))
    low = max(0.0, center - half)
    high = min(1.0, center + half)
    return (low, high)


class PlacementsAnalyzer(Analyzer):
    """Analyze RSYA placements for waste and performance."""

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.thresholds = {
            'min_cost': 500.0,
            'waste_cost_threshold': 2000.0,
            'min_clicks': 30,
        }
        self.thresholds.update(self.config.get('thresholds', {}))

    def analyze(self) -> list:
        """Run placements analysis."""
        min_cost = self.thresholds['min_cost']
        waste_cost = self.thresholds['waste_cost_threshold']
        min_clicks = self.thresholds['min_clicks']

        query = """
            SELECT
                account_id,
                placement,
                spend_rub,
                clicks,
                impressions,
                conversions
            FROM kpi_rsy_placements_7d
            WHERE spend_rub >= %s
            ORDER BY account_id, spend_rub DESC
        """
        
        rows = self.execute_query(query, (min_cost,))

        if not rows:
            return []

        # Group by account and analyze
        current_account = None
        acct_rows = []

        for row in rows:
            if row[0] != current_account:
                if current_account is not None:
                    self._analyze_account_placements(current_account, acct_rows, waste_cost, min_clicks)
                current_account = row[0]
                acct_rows = [row]
            else:
                acct_rows.append(row)

        # Analyze last account
        if current_account is not None:
            self._analyze_account_placements(current_account, acct_rows, waste_cost, min_clicks)

        return self.insights

    def _analyze_account_placements(self, account_id, rows, waste_cost, min_clicks):
        """Analyze placements for a single account."""
        # Calculate baseline CR for account
        total_clicks = sum(float(r[3] or 0) for r in rows)
        total_conversions = sum(float(r[5] or 0) for r in rows)

        if total_clicks == 0:
            return

        acct_cr = total_conversions / total_clicks
        acct_low, acct_high = wilson_interval(total_conversions, total_clicks)

        for r in rows:
            account_id_check, placement, spend_rub, clicks, impr, conv = r
            spend_rub = float(spend_rub or 0)
            clicks = float(clicks or 0)
            conv = float(conv or 0)

            # Waste: spend but no conversions
            if conv <= 0 and spend_rub >= waste_cost:
                confidence = min(1.0, clicks / 100)
                self.add_insight(
                    account_id=str(account_id),
                    type="RSYA_WASTE",
                    entity_type="placement",
                    entity_id=placement,
                    severity=0.8 * confidence,
                    impact_rub=spend_rub,
                    title=f"Плейсмент {placement}: расход без конверсий",
                    description=f"Потрачено {self.fmt_money(spend_rub)} руб., {int(clicks)} кликов, 0 конверсий",
                    recommendation=f"Исключить {placement} из RSYA",
                    evidence={
                        'placement': placement,
                        'clicks': clicks,
                        'spend_rub': float(spend_rub),
                        'conversions': 0,
                    },
                    confidence=confidence,
                )
                continue

            # Need enough clicks to make CR comparison meaningful
            if clicks < min_clicks:
                continue

            placement_low, placement_high = wilson_interval(conv, clicks)

            # Significantly worse CR than account
            if placement_high < acct_low:
                waste_rub = spend_rub * max(0.0, 1.0 - (conv / (clicks * acct_cr))) if acct_cr > 0 else spend_rub
                self.add_insight(
                    account_id=str(account_id),
                    type="RSYA_WASTE",
                    entity_type="placement",
                    entity_id=placement,
                    impact_rub=spend_rub,
                    title=f"Плейсмент {placement}: статистически ниже среднего",
                    description=f"CR {self.fmt_num(placement_low * 100)}-{self.fmt_num(placement_high * 100)}% vs средняя {self.fmt_num(acct_cr * 100)}%",
                    recommendation=f"Снизить ставки или исключить {placement}",
                    evidence={
                        'placement': placement,
                        'placement_cr_low': placement_low,
                        'placement_cr_high': placement_high,
                        'account_cr': acct_cr,
                        'clicks': clicks,
                        'conversions': float(conv),
                        'spend_rub': float(spend_rub),
                    },
                    confidence=0.9,
                )

            # Significantly better CR than account
            elif placement_low > acct_high:
                self.add_insight(
                    account_id=str(account_id),
                    type="RSYA_BEST",
                    entity_type="placement",
                    entity_id=placement,
                    impact_rub=spend_rub,
                    severity=0.3,
                    title=f"Плейсмент {placement}: лучше среднего",
                    description=f"CR {self.fmt_num(placement_low * 100)}-{self.fmt_num(placement_high * 100)}% vs средняя {self.fmt_num(acct_cr * 100)}%",
                    recommendation=f"Увеличить бюджет на {placement}",
                    evidence={
                        'placement': placement,
                        'placement_cr_low': placement_low,
                        'placement_cr_high': placement_high,
                        'account_cr': acct_cr,
                        'clicks': clicks,
                        'conversions': float(conv),
                        'spend_rub': float(spend_rub),
                    },
                    confidence=0.9,
                )


def main():
    """Run placements analysis."""
    analyzer = PlacementsAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()

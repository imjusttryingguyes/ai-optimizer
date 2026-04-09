"""
Segment (Device x Network) performance analysis.
Identifies worst, best, and wasting device/network combinations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .analyzer_base import Analyzer


class SegmentAnalyzer(Analyzer):
    """Analyze device × network segments for waste and performance."""

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.thresholds = {
            'min_cost': 1000.0,
            'waste_cost_threshold': 5000.0,
            'worst_multiplier': 1.5,
            'best_multiplier': 0.7,
        }
        self.thresholds.update(self.config.get('thresholds', {}))

    def analyze(self) -> list:
        """Run segment (device × network) analysis."""
        min_cost = self.thresholds['min_cost']
        waste_cost = self.thresholds['waste_cost_threshold']
        worst_mult = self.thresholds['worst_multiplier']
        best_mult = self.thresholds['best_multiplier']

        query = """
            SELECT
                account_id,
                device,
                ad_network_type,
                spend_rub,
                conversions,
                cpa_segment,
                cpa_account
            FROM kpi_segment_device_network
            WHERE spend_rub >= %s
            ORDER BY account_id, spend_rub DESC
        """
        
        rows = self.execute_query(query, (min_cost,))
        
        for account_id, device, net, spend_rub, conv, cpa_s, cpa_a in rows:
            spend_rub = float(spend_rub or 0)
            conv = float(conv or 0)

            # Waste: spend but no conversions
            if conv == 0 and spend_rub >= waste_cost:
                self.add_insight(
                    account_id=str(account_id),
                    type="SEGMENT_WASTE",
                    entity_type="segment",
                    entity_id=f"{device}_{net}",
                    impact_rub=spend_rub,
                    severity=min(spend_rub / 10000, 1.0),
                    title=f"Сегмент {device}/{net}: расход без конверсий",
                    description=f"Потрачено {self.fmt_money(spend_rub)} руб., но 0 конверсий",
                    recommendation=f"Остановить или пересмотреть рекламу на {device}/{net}",
                    evidence={
                        'device': device,
                        'network': net,
                        'spend_rub': float(spend_rub),
                        'conversions': 0,
                    },
                    confidence=0.95,
                )
                continue

            if cpa_s is None or cpa_a is None:
                continue

            cpa_s = float(cpa_s)
            cpa_a = float(cpa_a)

            # Worst segments
            if cpa_s > cpa_a * worst_mult:
                self.add_insight(
                    account_id=str(account_id),
                    type="SEGMENT_CPA_BAD",
                    entity_type="segment",
                    entity_id=f"{device}_{net}",
                    impact_rub=spend_rub,
                    title=f"Сегмент {device}/{net}: высокая CPA ({self.fmt_num(cpa_s)})",
                    description=f"CPA {self.fmt_num(cpa_s)} на {worst_mult}x выше средней по аккаунту ({self.fmt_num(cpa_a)})",
                    recommendation=f"Снизить ставки на {device}/{net}",
                    evidence={
                        'device': device,
                        'network': net,
                        'segment_cpa': cpa_s,
                        'account_cpa': cpa_a,
                        'conversions': float(conv),
                        'spend_rub': float(spend_rub),
                    },
                    confidence=0.9,
                )
            # Best segments
            elif cpa_s < cpa_a * best_mult:
                self.add_insight(
                    account_id=str(account_id),
                    type="SEGMENT_WINNER",
                    entity_type="segment",
                    entity_id=f"{device}_{net}",
                    impact_rub=spend_rub,
                    severity=0.2,
                    title=f"Сегмент {device}/{net}: отличная CPA ({self.fmt_num(cpa_s)})",
                    description=f"CPA {self.fmt_num(cpa_s)} на {1/best_mult:.1f}x ниже средней",
                    recommendation=f"Увеличить бюджет на {device}/{net}",
                    evidence={
                        'device': device,
                        'network': net,
                        'segment_cpa': cpa_s,
                        'account_cpa': cpa_a,
                        'conversions': float(conv),
                        'spend_rub': float(spend_rub),
                    },
                    confidence=0.85,
                )

        return self.insights


def main():
    """Run segment analysis."""
    analyzer = SegmentAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()

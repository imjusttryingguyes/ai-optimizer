"""
Segment ladder trend analysis.
Detects improving/worsening hierarchical segments over time.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .analyzer_base import Analyzer


class SegmentLadderTrendAnalyzer(Analyzer):
    """Analyze trends in hierarchical segment dimensions."""

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.thresholds = {
            'min_spend_recent': 1000,
            'min_clicks_recent': 15,
            'cpa_bad_threshold': 1.3,
            'cpa_good_threshold': 0.7,
        }
        self.thresholds.update(self.config.get('thresholds', {}))

    def analyze(self) -> list:
        """Run segment ladder trend analysis."""
        query = """
            SELECT
                account_id,
                age,
                gender,
                device,
                ad_network_type,
                data_days_recent_7d,
                data_days_baseline_23d,
                spend_recent_7d,
                spend_baseline_23d,
                conversions_recent_7d,
                conversions_baseline_23d,
                cpa_recent_7d,
                cpa_baseline_23d,
                clicks_recent_7d,
                clicks_baseline_23d
            FROM kpi_segment_ladder_trend_30d
        """
        
        rows = self.execute_query(query)
        
        for row in rows:
            (account_id, age, gender, device, network,
             data_recent, data_baseline, spend_recent, spend_baseline,
             conv_recent, conv_baseline, cpa_recent, cpa_baseline,
             clicks_recent, clicks_baseline) = row

            data_recent = int(data_recent or 0)
            data_baseline = int(data_baseline or 0)
            spend_recent = float(spend_recent or 0)
            spend_baseline = float(spend_baseline or 0)
            conv_recent = float(conv_recent or 0)
            conv_baseline = float(conv_baseline or 0)
            cpa_recent = float(cpa_recent) if cpa_recent else None
            cpa_baseline = float(cpa_baseline) if cpa_baseline else None

            if data_recent < 3 or data_baseline < 15:
                continue

            if spend_recent < self.thresholds['min_spend_recent']:
                continue

            if not cpa_recent or not cpa_baseline or cpa_baseline == 0:
                continue

            segment_label = f"{age} / {gender} / {device} / {network}"

            # CPA got worse
            if cpa_recent > cpa_baseline * self.thresholds['cpa_bad_threshold']:
                change_pct = ((cpa_recent - cpa_baseline) / cpa_baseline) * 100
                self.add_insight(
                    account_id=str(account_id),
                    type="SEGMENT_LADDER_TREND_BAD",
                    entity_type="segment_ladder",
                    entity_id=f"{age}|{gender}|{device}|{network}",
                    impact_rub=spend_recent,
                    title=f"Сегмент: CPA ухудшилась на {change_pct:.0f}%",
                    description=f"{segment_label}\nCPA за 7 дней: {self.fmt_num(cpa_recent)}, за 23 дня: {self.fmt_num(cpa_baseline)}",
                    recommendation="Проверить ставки и параметры таргетинга",
                    evidence={
                        'segment': segment_label,
                        'cpa_recent': cpa_recent,
                        'cpa_baseline': cpa_baseline,
                        'change_pct': change_pct,
                        'spend_recent': spend_recent,
                    },
                    confidence=0.75,
                )

            # CPA got better
            elif cpa_recent < cpa_baseline * self.thresholds['cpa_good_threshold']:
                change_pct = ((cpa_baseline - cpa_recent) / cpa_baseline) * 100
                self.add_insight(
                    account_id=str(account_id),
                    type="SEGMENT_LADDER_TREND_GOOD",
                    entity_type="segment_ladder",
                    entity_id=f"{age}|{gender}|{device}|{network}",
                    impact_rub=spend_recent,
                    severity=0.5,
                    title=f"Сегмент: CPA улучшилась на {change_pct:.0f}%",
                    description=f"{segment_label}\nCPA за 7 дней: {self.fmt_num(cpa_recent)}, за 23 дня: {self.fmt_num(cpa_baseline)}",
                    recommendation="Увеличить бюджет на этот сегмент",
                    evidence={
                        'segment': segment_label,
                        'cpa_recent': cpa_recent,
                        'cpa_baseline': cpa_baseline,
                        'change_pct': change_pct,
                        'spend_recent': spend_recent,
                    },
                    confidence=0.75,
                )

        return self.insights


def main():
    """Run segment ladder trend analysis."""
    analyzer = SegmentLadderTrendAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()

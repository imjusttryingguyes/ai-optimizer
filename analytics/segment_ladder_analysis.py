"""
Segment ladder analysis (30 day window).
Detects performance variations across segment hierarchies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .analyzer_base import Analyzer


class SegmentLadderAnalyzer(Analyzer):
    """Analyze hierarchical segment dimensions (ladder)."""

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.thresholds = {
            'min_spend': 2000,
            'min_clicks': 20,
            'min_conversions': 1,
            'cpa_bad_multiplier': 1.5,
            'cpa_good_multiplier': 0.75,
        }
        self.thresholds.update(self.config.get('thresholds', {}))

    def analyze(self) -> list:
        """Run segment ladder analysis."""
        # Fetch account CPA baseline
        acct_query = "SELECT account_id, cpa FROM kpi_account_30d WHERE cpa IS NOT NULL AND cpa > 0"
        acct_rows = self.execute_query(acct_query)
        acct_cpa_map = {str(row[0]): float(row[1]) for row in acct_rows}

        # Main query for segment ladder data
        query = """
            SELECT
                account_id,
                age,
                gender,
                device,
                ad_network_type,
                SUM(spend_rub) AS spend_rub,
                SUM(clicks) AS clicks,
                SUM(conversions) AS conversions,
                CASE
                    WHEN SUM(conversions) > 0
                        THEN SUM(spend_rub) / SUM(conversions)
                    ELSE NULL
                END AS segment_cpa
            FROM kpi_segment_ladder_30d
            GROUP BY account_id, age, gender, device, ad_network_type
        """
        
        rows = self.execute_query(query)
        
        for row in rows:
            (account_id, age, gender, device, network, spend_rub, clicks,
             conversions, segment_cpa) = row

            account_id_str = str(account_id)
            spend_rub = float(spend_rub or 0)
            clicks = int(clicks or 0)
            conversions = float(conversions or 0)
            segment_cpa = float(segment_cpa) if segment_cpa else None

            # Skip unknowns and insufficient data
            if not all([age, gender, device, network]) or any(str(v).upper() == "UNKNOWN" for v in [age, gender, device, network]):
                continue

            if spend_rub < self.thresholds['min_spend']:
                continue

            acct_cpa = acct_cpa_map.get(account_id_str)
            if not acct_cpa or not segment_cpa:
                continue

            segment_label = f"{age} / {gender} / {device} / {network}"

            # Bad CPA segment
            if segment_cpa > acct_cpa * self.thresholds['cpa_bad_multiplier']:
                self.add_insight(
                    account_id=account_id_str,
                    type="SEGMENT_LADDER_CPA_BAD",
                    entity_type="segment_ladder",
                    entity_id=f"{age}|{gender}|{device}|{network}",
                    impact_rub=spend_rub,
                    title=f"Сегмент {segment_label}: высокая CPA",
                    description=f"CPA {self.fmt_num(segment_cpa)} vs средняя {self.fmt_num(acct_cpa)}",
                    recommendation="Пересмотреть ставки для этого сегмента",
                    evidence={
                        'segment_label': segment_label,
                        'segment_cpa': segment_cpa,
                        'account_cpa': acct_cpa,
                        'clicks': clicks,
                        'conversions': conversions,
                        'spend_rub': spend_rub,
                    },
                    confidence=0.8,
                )

            # Good CPA segment
            elif segment_cpa < acct_cpa * self.thresholds['cpa_good_multiplier']:
                self.add_insight(
                    account_id=account_id_str,
                    type="SEGMENT_LADDER_WINNER",
                    entity_type="segment_ladder",
                    entity_id=f"{age}|{gender}|{device}|{network}",
                    impact_rub=spend_rub,
                    severity=0.3,
                    title=f"Сегмент {segment_label}: отличная CPA",
                    description=f"CPA {self.fmt_num(segment_cpa)} vs средняя {self.fmt_num(acct_cpa)}",
                    recommendation="Увеличить бюджет для этого сегмента",
                    evidence={
                        'segment_label': segment_label,
                        'segment_cpa': segment_cpa,
                        'account_cpa': acct_cpa,
                        'clicks': clicks,
                        'conversions': conversions,
                        'spend_rub': spend_rub,
                    },
                    confidence=0.8,
                )

        return self.insights


def main():
    """Run segment ladder analysis."""
    analyzer = SegmentLadderAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()

"""
Segment combinations analysis (30 day window).
Detects problematic and high-performing segment combinations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .analyzer_base import Analyzer


class SegmentCombinationsAnalyzer(Analyzer):
    """Analyze combinations of targeting dimensions."""

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.thresholds = {
            'min_spend': 4000,
            'min_clicks': 30,
            'min_spend_cpa_bad': 5000,
            'min_clicks_cpa_bad': 50,
            'min_conversions_cpa_bad': 2,
            'cpa_bad_multiplier': 1.8,
            'min_spend_winner': 5000,
            'min_clicks_winner': 30,
            'min_conversions_winner': 2,
            'winner_cpa_multiplier': 0.6,
        }
        self.thresholds.update(self.config.get('thresholds', {}))

    @staticmethod
    def has_unknown_values(*values):
        """Check if any values are missing or invalid."""
        for value in values:
            if value is None:
                return True
            if isinstance(value, str) and not value.strip():
                return True
            if isinstance(value, (int, float)) and value == 0:
                return True
            if str(value).upper() == "UNKNOWN":
                return True
        return False

    @staticmethod
    def build_segment_label(campaign_id, adgroup_id, criterion_id, device, ad_network_type,
                           location_of_presence, targeting_location, age, gender, weekday):
        """Build human-readable segment label."""
        parts = [
            f"weekday={weekday}",
            f"campaign={campaign_id}",
            f"adgroup={adgroup_id}",
            f"criterion={criterion_id}",
        ]
        if location_of_presence:
            parts.append(f"location={location_of_presence}")
        if targeting_location:
            parts.append(f"targeting={targeting_location}")
        parts.extend([
            f"device={device}",
            f"age={age}",
            f"gender={gender}",
            f"network={ad_network_type}",
        ])
        return ", ".join(parts)

    def analyze(self) -> list:
        """Run segment combinations analysis."""
        query = """
            SELECT
                sc.account_id,
                sc.client_login,
                sc.campaign_id,
                sc.adgroup_id,
                sc.criterion_id,
                sc.ad_network_type,
                sc.device,
                sc.location_of_presence_name,
                sc.targeting_location_name,
                sc.age,
                sc.gender,
                sc.weekday,
                SUM(sc.impressions) AS impressions,
                SUM(sc.clicks) AS clicks,
                SUM(sc.spend_rub) AS spend_rub,
                SUM(sc.conversions) AS conversions,
                CASE
                    WHEN SUM(sc.conversions) > 0
                        THEN SUM(sc.spend_rub) / SUM(sc.conversions)
                    ELSE NULL
                END AS segment_cpa,
                acc.cpa AS account_cpa
            FROM kpi_segment_combinations_30d sc
            LEFT JOIN kpi_account_30d acc
                ON acc.account_id = sc.account_id
            GROUP BY
                sc.account_id, sc.client_login, sc.campaign_id, sc.adgroup_id,
                sc.criterion_id, sc.ad_network_type, sc.device,
                sc.location_of_presence_name, sc.targeting_location_name,
                sc.age, sc.gender, sc.weekday, acc.cpa
        """
        
        rows = self.execute_query(query)
        
        for row in rows:
            (account_id, client_login, campaign_id, adgroup_id, criterion_id,
             ad_network_type, device, location_of_presence, targeting_location,
             age, gender, weekday, impressions, clicks, spend_rub, conversions,
             segment_cpa, account_cpa) = row

            spend_rub = float(spend_rub or 0)
            clicks = int(clicks or 0)
            conversions = float(conversions or 0)
            segment_cpa = float(segment_cpa) if segment_cpa else None
            account_cpa = float(account_cpa) if account_cpa else None

            # Skip if unknown values
            if self.has_unknown_values(campaign_id, adgroup_id, criterion_id, ad_network_type,
                                       device, location_of_presence, targeting_location,
                                       age, gender, weekday):
                continue

            if spend_rub < self.thresholds['min_spend']:
                continue

            # Bad CPA combination
            if (spend_rub >= self.thresholds['min_spend_cpa_bad'] and
                clicks >= self.thresholds['min_clicks_cpa_bad'] and
                conversions >= self.thresholds['min_conversions_cpa_bad'] and
                segment_cpa and account_cpa and account_cpa > 0 and
                segment_cpa > account_cpa * self.thresholds['cpa_bad_multiplier']):

                label = self.build_segment_label(campaign_id, adgroup_id, criterion_id, device,
                                                 ad_network_type, location_of_presence,
                                                 targeting_location, age, gender, weekday)
                self.add_insight(
                    account_id=str(account_id),
                    type="SEGMENT_COMBINATION_CPA_BAD",
                    entity_type="segment_combination",
                    entity_id=f"{weekday}|{campaign_id}|{adgroup_id}|{criterion_id}|{device}|{age}|{gender}",
                    impact_rub=spend_rub,
                    title=f"Комбинация сегментов: высокая CPA",
                    description=f"CPA {self.fmt_num(segment_cpa)} vs средняя {self.fmt_num(account_cpa)}\n{label}",
                    recommendation="Снизить ставки или исключить эту комбинацию",
                    evidence={
                        'segment_label': label,
                        'segment_cpa': segment_cpa,
                        'account_cpa': account_cpa,
                        'clicks': clicks,
                        'conversions': conversions,
                        'spend_rub': spend_rub,
                    },
                    confidence=0.85,
                )

            # Winner combination
            if (spend_rub >= self.thresholds['min_spend_winner'] and
                clicks >= self.thresholds['min_clicks_winner'] and
                conversions >= self.thresholds['min_conversions_winner'] and
                segment_cpa and account_cpa and account_cpa > 0 and
                segment_cpa < account_cpa * self.thresholds['winner_cpa_multiplier']):

                label = self.build_segment_label(campaign_id, adgroup_id, criterion_id, device,
                                                 ad_network_type, location_of_presence,
                                                 targeting_location, age, gender, weekday)
                self.add_insight(
                    account_id=str(account_id),
                    type="SEGMENT_COMBINATION_WINNER",
                    entity_type="segment_combination",
                    entity_id=f"{weekday}|{campaign_id}|{adgroup_id}|{criterion_id}|{device}|{age}|{gender}",
                    impact_rub=spend_rub,
                    severity=0.3,
                    title=f"Комбинация сегментов: отличная CPA",
                    description=f"CPA {self.fmt_num(segment_cpa)} vs средняя {self.fmt_num(account_cpa)}\n{label}",
                    recommendation="Увеличить бюджет на эту комбинацию",
                    evidence={
                        'segment_label': label,
                        'segment_cpa': segment_cpa,
                        'account_cpa': account_cpa,
                        'clicks': clicks,
                        'conversions': conversions,
                        'spend_rub': spend_rub,
                    },
                    confidence=0.85,
                )

        return self.insights


def main():
    """Run segment combinations analysis."""
    analyzer = SegmentCombinationsAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()

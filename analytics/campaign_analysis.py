"""
Campaign-level performance analysis.
Identifies worst, best, and wasting campaigns relative to account average.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .analyzer_base import Analyzer


class CampaignAnalyzer(Analyzer):
    """Analyze campaigns within each account for waste and winners."""

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
        """Run campaign analysis."""
        min_cost = self.thresholds['min_cost']
        waste_cost = self.thresholds['waste_cost_threshold']
        worst_mult = self.thresholds['worst_multiplier']
        best_mult = self.thresholds['best_multiplier']

        query = """
            SELECT
                account_id,
                campaign_id,
                spend_rub,
                conversions,
                cpa,
                AVG(cpa) OVER (PARTITION BY account_id) as cpa_account
            FROM kpi_campaign_vs_account
            WHERE spend_rub >= %s
            ORDER BY account_id, spend_rub DESC
        """
        
        rows = self.execute_query(query, (min_cost,))
        
        current_account = None
        worst = []
        best = []
        waste = []

        for r in rows:
            account_id, campaign_id, spend_rub, conv, cpa_c, cpa_a = r

            if account_id != current_account:
                if current_account is not None:
                    self._save_campaign_insights(current_account, worst, best, waste)
                current_account = account_id
                worst, best, waste = [], [], []

            spend_rub = float(spend_rub or 0)
            conv = float(conv or 0)
            cpa_a = float(cpa_a) if cpa_a is not None else None
            cpa_c = float(cpa_c) if cpa_c is not None else None

            # Waste: spend but no conversions
            if conv == 0 and spend_rub >= waste_cost:
                waste.append((campaign_id, spend_rub))
                continue

            if cpa_a is None or cpa_c is None:
                continue

            # Worst/best relative to account CPA
            if cpa_c > cpa_a * worst_mult:
                worst.append((campaign_id, spend_rub, conv, cpa_c, cpa_a))
            elif cpa_c < cpa_a * best_mult:
                best.append((campaign_id, spend_rub, conv, cpa_c, cpa_a))

        # Save last account's insights
        if current_account is not None:
            self._save_campaign_insights(current_account, worst, best, waste)

        return self.insights

    def _save_campaign_insights(self, account_id, worst, best, waste):
        """Save campaign insights for single account."""
        # Worst campaigns
        for cid, spend_rub, conv, cpa_c, cpa_a in worst[:10]:
            self.add_insight(
                account_id=str(account_id),
                type="CAMPAIGN_CPA_BAD",
                entity_type="campaign",
                entity_id=str(cid),
                impact_rub=spend_rub,
                title=f"Кампания {cid}: высокая CPA ({self.fmt_num(cpa_c)} vs {self.fmt_num(cpa_a)})",
                description=f"CPA этой кампании {self.fmt_num(cpa_c)} на {self.thresholds['worst_multiplier']}x выше средней по аккаунту",
                recommendation=f"Пересмотреть ставки и целевые группы в кампании {cid}",
                evidence={
                    'campaign_cpa': float(cpa_c),
                    'account_cpa': float(cpa_a),
                    'conversions': float(conv),
                    'spend_rub': float(spend_rub),
                },
                confidence=0.9,
            )

        # Waste campaigns (spend but no conversions)
        for cid, spend_rub in waste[:10]:
            self.add_insight(
                account_id=str(account_id),
                type="CAMPAIGN_WASTE",
                entity_type="campaign",
                entity_id=str(cid),
                impact_rub=spend_rub,
                severity=min(spend_rub / 10000, 1.0),
                title=f"Кампания {cid}: расход без конверсий",
                description=f"Потрачено {self.fmt_money(spend_rub)} руб., но 0 конверсий",
                recommendation=f"Остановить или пересмотреть кампанию {cid}",
                evidence={
                    'spend_rub': float(spend_rub),
                    'conversions': 0,
                },
                confidence=0.95,
            )

        # Best campaigns
        for cid, spend_rub, conv, cpa_c, cpa_a in best[:5]:
            self.add_insight(
                account_id=str(account_id),
                type="CAMPAIGN_WINNER",
                entity_type="campaign",
                entity_id=str(cid),
                impact_rub=spend_rub,
                severity=0.2,
                title=f"Кампания {cid}: отличная CPA ({self.fmt_num(cpa_c)})",
                description=f"CPA этой кампании {self.fmt_num(cpa_c)} на {1/self.thresholds['best_multiplier']:.1f}x ниже средней",
                recommendation=f"Увеличить бюджет кампании {cid}",
                evidence={
                    'campaign_cpa': float(cpa_c),
                    'account_cpa': float(cpa_a),
                    'conversions': float(conv),
                    'spend_rub': float(spend_rub),
                },
                confidence=0.85,
            )


def main():
    """Run campaign analysis."""
    analyzer = CampaignAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()

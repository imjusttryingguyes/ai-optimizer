"""
Analyzer configuration.
Centralized thresholds and settings for all analyzers.
"""

ANALYZER_CONFIG = {
    'campaign': {
        'thresholds': {
            'min_cost': 1000.0,
            'waste_cost_threshold': 5000.0,
            'worst_multiplier': 1.5,
            'best_multiplier': 0.7,
        }
    },
    'segment': {
        'thresholds': {
            'min_cost': 1000.0,
            'waste_cost_threshold': 5000.0,
            'worst_multiplier': 1.5,
            'best_multiplier': 0.7,
        }
    },
    'trend': {
        'thresholds': {
            'min_data_days_last': 2,
            'min_data_days_prev': 3,
            'cpa_bad_threshold': 1.3,
            'cpa_good_threshold': 0.7,
            'leads_bad_threshold': 0.7,
            'leads_good_threshold': 1.5,
        }
    },
    'placements': {
        'thresholds': {
            'min_cost': 500.0,
            'waste_cost_threshold': 2000.0,
            'min_clicks': 30,
        }
    },
    'kpi_alert': {
        'thresholds': {}
    },
    'segment_combinations': {
        'thresholds': {
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
    },
    'segment_ladder': {
        'thresholds': {
            'min_spend': 2000,
            'min_clicks': 20,
            'min_conversions': 1,
            'cpa_bad_multiplier': 1.5,
            'cpa_good_multiplier': 0.75,
        }
    },
    'segment_combinations_trend': {
        'thresholds': {
            'min_spend_recent': 2000,
            'min_clicks_recent': 20,
            'min_conversions_recent': 1,
            'cpa_bad_threshold': 1.3,
            'cpa_good_threshold': 0.7,
        }
    },
    'segment_ladder_trend': {
        'thresholds': {
            'min_spend_recent': 1000,
            'min_clicks_recent': 15,
            'cpa_bad_threshold': 1.3,
            'cpa_good_threshold': 0.7,
        }
    },
}


def get_analyzer_config(analyzer_name: str) -> dict:
    """Get configuration for specific analyzer."""
    return ANALYZER_CONFIG.get(analyzer_name, {'thresholds': {}})

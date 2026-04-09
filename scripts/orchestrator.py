"""
Analyzer registry.
Central place to manage and execute all analyzers.
"""

import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from analytics.config import get_analyzer_config
from analytics.campaign_analysis import CampaignAnalyzer
from analytics.segment_analysis import SegmentAnalyzer
from analytics.trend_analysis import TrendAnalyzer
from analytics.placements_analysis import PlacementsAnalyzer
from analytics.kpi_alert import KPIAlertAnalyzer
from analytics.segment_combinations_analysis import SegmentCombinationsAnalyzer
from analytics.segment_ladder_analysis import SegmentLadderAnalyzer
from analytics.segment_combinations_trend_analysis import SegmentCombinationsTrendAnalyzer
from analytics.segment_ladder_trend_analysis import SegmentLadderTrendAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Registry of all analyzers
ANALYZERS = [
    ('placements', PlacementsAnalyzer),
    ('campaign', CampaignAnalyzer),
    ('segment', SegmentAnalyzer),
    ('segment_combinations', SegmentCombinationsAnalyzer),
    ('segment_ladder', SegmentLadderAnalyzer),
    ('segment_combinations_trend', SegmentCombinationsTrendAnalyzer),
    ('segment_ladder_trend', SegmentLadderTrendAnalyzer),
    ('trend', TrendAnalyzer),
    ('kpi_alert', KPIAlertAnalyzer),
]


def run_analyzer(name: str) -> bool:
    """Run a single analyzer by name."""
    for analyzer_name, analyzer_class in ANALYZERS:
        if analyzer_name == name:
            try:
                logger.info(f"Starting {analyzer_name}")
                config = get_analyzer_config(analyzer_name)
                analyzer = analyzer_class(config)
                analyzer.run()
                logger.info(f"Completed {analyzer_name}")
                return True
            except Exception as e:
                logger.error(f"Error in {analyzer_name}: {e}", exc_info=True)
                return False
    
    logger.warning(f"Analyzer '{name}' not found")
    return False


def run_all_analyzers() -> int:
    """Run all analyzers sequentially."""
    failed = []
    for analyzer_name, _ in ANALYZERS:
        if not run_analyzer(analyzer_name):
            failed.append(analyzer_name)
    
    if failed:
        logger.error(f"Failed analyzers: {', '.join(failed)}")
        return len(failed)
    
    logger.info("All analyzers completed successfully")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyzer_name = sys.argv[1]
        success = run_analyzer(analyzer_name)
        sys.exit(0 if success else 1)
    else:
        sys.exit(run_all_analyzers())

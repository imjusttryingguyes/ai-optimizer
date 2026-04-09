"""
Base class for all analyzers in AI Optimizer.
Provides common utilities: DB connection, formatting, logging.
"""

import os
import sys
import logging
import psycopg2
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from insight_utils import insert_insight

load_dotenv()

logger = logging.getLogger(__name__)


class Analyzer:
    """Base class for all account analyzers."""

    def __init__(self, config: dict = None):
        """
        Initialize analyzer with optional config.
        
        Args:
            config: dict with 'thresholds' and other analyzer-specific settings
        """
        self.config = config or {}
        self.thresholds = self.config.get('thresholds', {})
        self.insights = []

    @staticmethod
    def get_conn():
        """Get PostgreSQL connection."""
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

    @staticmethod
    def fmt_money(x) -> str:
        """Format money value (rubles) with space separators."""
        try:
            return f"{float(x):,.0f}".replace(",", " ")
        except (ValueError, TypeError):
            return str(x)

    @staticmethod
    def fmt_num(x) -> str:
        """Format number with 2 decimal places and space separators."""
        try:
            return f"{float(x):,.2f}".replace(",", " ")
        except (ValueError, TypeError):
            return str(x)

    def analyze(self) -> list:
        """
        Run analysis and return list of insights.
        Must be implemented by subclasses.
        
        Returns:
            list of dicts with insight parameters for insert_insight()
        """
        raise NotImplementedError("Subclasses must implement analyze()")

    def run(self):
        """Execute analysis and save insights to database."""
        try:
            logger.info(f"Starting {self.__class__.__name__}")
            self.insights = self.analyze()
            
            for insight in self.insights:
                insert_insight(**insight)
            
            logger.info(f"{self.__class__.__name__} completed. Saved {len(self.insights)} insights")
            return self.insights
        except Exception as e:
            logger.error(f"Error in {self.__class__.__name__}: {e}", exc_info=True)
            raise

    def execute_query(self, query: str, params: tuple = None):
        """Execute SQL query and return results."""
        conn = self.get_conn()
        cur = conn.cursor()
        try:
            cur.execute(query, params or ())
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

    def add_insight(
        self,
        account_id: str,
        type: str,
        entity_type: str,
        entity_id: str = None,
        severity: float = None,
        impact_rub: float = None,
        title: str = None,
        description: str = None,
        recommendation: str = None,
        evidence: dict = None,
        confidence: float = 1.0,
        insight_date: str = None,
    ):
        """Add insight to the list (will be saved by run())."""
        self.insights.append({
            'account_id': account_id,
            'type': type,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'severity': severity,
            'impact_rub': impact_rub,
            'title': title,
            'description': description,
            'recommendation': recommendation,
            'evidence': evidence,
            'confidence': confidence,
            'insight_date': insight_date,
        })

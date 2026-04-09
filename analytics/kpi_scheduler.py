"""
Background task scheduler for KPI updates
Uses APScheduler for background task management (optional)
"""

import logging
import os
import psycopg2

logger = logging.getLogger(__name__)

# Try to import APScheduler, fall back gracefully
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not available - background tasks disabled. Install with: pip install apscheduler")

from analytics.kpi_sync_task import KPIDailySync


class KPIScheduler:
    """Manage background KPI tasks"""
    
    _instance = None
    _scheduler = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super(KPIScheduler, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def initialize(cls, app=None, db_url: str = None):
        """
        Initialize scheduler
        
        Args:
            app: Flask app instance (optional)
            db_url: Database URL for connection
        """
        if not APSCHEDULER_AVAILABLE:
            logger.warning("Skipping scheduler init - APScheduler not installed")
            return
        
        scheduler_instance = cls()
        
        if scheduler_instance._scheduler is None:
            scheduler_instance._scheduler = BackgroundScheduler()
            scheduler_instance._db_url = db_url
            scheduler_instance._app = app
            
            # Add KPI daily sync job (11 PM nightly)
            scheduler_instance._scheduler.add_job(
                func=scheduler_instance._daily_kpi_sync,
                trigger=CronTrigger(hour=23, minute=0),
                id='daily_kpi_sync',
                name='Daily KPI Sync',
                replace_existing=True,
                max_instances=1
            )
            
            logger.info("KPI Scheduler initialized with daily sync at 23:00")
            
            if app:
                scheduler_instance._scheduler.start()
                logger.info("Background scheduler started")
    
    @classmethod
    def start(cls):
        """Start the scheduler"""
        if not APSCHEDULER_AVAILABLE:
            return
        
        scheduler_instance = cls()
        if scheduler_instance._scheduler and not scheduler_instance._scheduler.running:
            scheduler_instance._scheduler.start()
            logger.info("Scheduler started")
    
    @classmethod
    def stop(cls):
        """Stop the scheduler"""
        if not APSCHEDULER_AVAILABLE:
            return
        
        scheduler_instance = cls()
        if scheduler_instance._scheduler and scheduler_instance._scheduler.running:
            scheduler_instance._scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    @staticmethod
    def _daily_kpi_sync():
        """Background task: Daily KPI synchronization"""
        logger.info("=" * 60)
        logger.info("Starting daily KPI sync task")
        logger.info("=" * 60)
        
        try:
            # Get database connection
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                # Build from individual env vars
                conn = psycopg2.connect(
                    host=os.getenv("DB_HOST"),
                    port=os.getenv("DB_PORT", 5432),
                    dbname=os.getenv("DB_NAME"),
                    user=os.getenv("DB_USER"),
                    password=os.getenv("DB_PASSWORD")
                )
            else:
                conn = psycopg2.connect(db_url)
            
            # Get tokens
            yandex_token = os.getenv("YANDEX_API_TOKEN")
            telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
            
            if not yandex_token:
                logger.error("YANDEX_API_TOKEN not configured")
                return
            
            # Run sync
            sync_task = KPIDailySync(conn, yandex_token, telegram_token)
            result = sync_task.sync_all_accounts()
            
            # Log results
            logger.info(f"Daily sync completed:")
            logger.info(f"  Status: {result['status']}")
            logger.info(f"  Accounts processed: {result['accounts_processed']}")
            logger.info(f"  Accounts failed: {result['accounts_failed']}")
            
            if result['errors']:
                logger.warning(f"  Errors: {result['errors']}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Fatal error in daily KPI sync: {e}", exc_info=True)
    
    @classmethod
    def get_jobs(cls):
        """Get list of scheduled jobs"""
        if not APSCHEDULER_AVAILABLE:
            return []
        
        scheduler_instance = cls()
        if scheduler_instance._scheduler:
            return scheduler_instance._scheduler.get_jobs()
        return []
    
    @classmethod
    def get_job_info(cls):
        """Get detailed job information"""
        if not APSCHEDULER_AVAILABLE:
            return []
        
        scheduler_instance = cls()
        jobs_info = []
        
        if scheduler_instance._scheduler:
            for job in scheduler_instance._scheduler.get_jobs():
                jobs_info.append({
                    "id": job.id,
                    "name": job.name,
                    "trigger": str(job.trigger),
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "status": "running" if scheduler_instance._scheduler.running else "stopped"
                })
        
        return jobs_info


def init_scheduler(app, db_url: str = None):
    """
    Initialize KPI scheduler with Flask app
    
    Args:
        app: Flask application instance
        db_url: Database connection URL (optional)
    """
    KPIScheduler.initialize(app, db_url)

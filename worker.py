#!/usr/bin/env python3
"""
Background Worker - Processes jobs from database queue
Runs continuously, picking up jobs submitted by frontend
Also runs daily cleanup of old jobs and expired cache
"""
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator.job_processor_postgres import JobProcessorPostgres
from database.postgres_models import PostgresDatabase, JobManager
from scripts.cleanup_old_data_postgres import run_cleanup

# Configure logging to write to both file and console
def setup_logging():
    """Setup logging to write to both file and console"""
    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/worker_{timestamp}.log"

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers
    root_logger.handlers = []

    # Add file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Add console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Log initialization
    root_logger.info("="*80)
    root_logger.info(f"Logging initialized - writing to: {log_file}")
    root_logger.info("="*80)

    return log_file

# Setup logging
log_file_path = setup_logging()
logger = logging.getLogger(__name__)


def main():
    """Main worker loop - processes jobs from queue"""
    logger.info("="*80)
    logger.info("DEALERSHIP SCRAPER BACKGROUND WORKER STARTING")
    logger.info("="*80)

    # Initialize job processor with PostgreSQL
    processor = JobProcessorPostgres(
        database_url=os.getenv("DATABASE_URL"),  # Render provides this automatically
        cache_ttl_days=int(os.getenv("CACHE_TTL_DAYS", "7")),
        scraper_max_retries=int(os.getenv("SCRAPER_MAX_RETRIES", "2")),
        email_max_retries=int(os.getenv("EMAIL_MAX_RETRIES", "3"))
    )

    logger.info("✓ Job processor initialized")
    logger.info(f"  Cache TTL: {processor.cache_mgr.cache_ttl_days} days")
    logger.info(f"  Scraper retries: {processor.scraper_max_retries}")
    logger.info(f"  Email retries: {processor.email_max_retries}")
    logger.info("")

    # Worker loop
    poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
    cleanup_retention_days = int(os.getenv("CLEANUP_RETENTION_DAYS", "7"))
    logger.info(f"Worker polling every {poll_interval} seconds for new jobs...")
    logger.info(f"Cleanup runs daily for jobs older than {cleanup_retention_days} days")
    logger.info("="*80)

    # Track last cleanup time
    last_cleanup_time = datetime.now() - timedelta(days=1)  # Run cleanup on first iteration

    while True:
        try:
            # Check if it's time to run daily cleanup (once every 24 hours)
            time_since_last_cleanup = datetime.now() - last_cleanup_time
            if time_since_last_cleanup >= timedelta(hours=24):
                logger.info("\n" + "="*80)
                logger.info("⏰ RUNNING DAILY CLEANUP")
                logger.info("="*80)
                try:
                    cleanup_success = run_cleanup(
                        retention_days=cleanup_retention_days,
                        dry_run=False,
                        cache_only=False,
                        jobs_only=False
                    )
                    if cleanup_success:
                        logger.info("✅ Daily cleanup completed successfully")
                        last_cleanup_time = datetime.now()
                    else:
                        logger.warning("⚠️  Daily cleanup completed with errors")
                except Exception as e:
                    logger.error(f"❌ Daily cleanup failed: {str(e)}", exc_info=True)
                logger.info("="*80 + "\n")

            # Get queued jobs
            queued_jobs = processor.job_mgr.get_queued_jobs(limit=1)

            if queued_jobs:
                job = queued_jobs[0]
                job_id = job['job_id']

                logger.info(f"\n{'='*80}")
                logger.info(f"📥 NEW JOB FOUND: {job_id}")
                logger.info(f"{'='*80}")
                logger.info(f"Client: {job['client_name']}")
                logger.info(f"Email: {job['client_email']}")
                logger.info(f"Submitted: {job['created_at']}")
                logger.info("")

                # Process job
                try:
                    success = processor.process_job(job_id)

                    if success:
                        logger.info(f"\n✅ JOB COMPLETED: {job_id}")
                    else:
                        logger.error(f"\n❌ JOB FAILED: {job_id}")

                except Exception as e:
                    logger.error(f"\n❌ JOB ERROR: {job_id}")
                    logger.error(f"Error: {str(e)}", exc_info=True)

                    # Update job status to failed
                    processor.job_mgr.update_status(
                        job_id=job_id,
                        status='failed',
                        error_message=f"Worker exception: {str(e)}"
                    )

                logger.info(f"\n{'='*80}\n")

            else:
                # No jobs, sleep
                time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("\n\n⚠️  Worker interrupted by user (Ctrl+C)")
            logger.info("Shutting down gracefully...")
            break

        except Exception as e:
            logger.error(f"Worker loop error: {str(e)}", exc_info=True)
            logger.warning("Sleeping 30 seconds before retry...")
            time.sleep(30)

    logger.info("="*80)
    logger.info("WORKER SHUTDOWN COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()

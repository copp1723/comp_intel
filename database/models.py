"""
Database Models for Job Tracking and Cache Management
SQLite-based persistence layer
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import threading
from contextlib import contextmanager


class Database:
    """Thread-safe SQLite database manager"""

    def __init__(self, db_path: str = "data/database.db"):
        self.db_path = db_path
        self._local = threading.local()

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0  # 30 second timeout for locks
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection

    @contextmanager
    def get_cursor(self):
        """Context manager for database operations with auto-commit"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def _initialize_schema(self):
        """Create database tables if they don't exist"""
        with self.get_cursor() as cursor:
            # Jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    client_name TEXT NOT NULL,
                    client_email TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    progress_percentage INTEGER DEFAULT 0,
                    current_step TEXT,
                    total_steps INTEGER DEFAULT 0,
                    completed_steps INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    data_folder TEXT,
                    metadata TEXT
                )
            """)

            # Scraped sites cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraped_sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    dealership_name TEXT NOT NULL,
                    last_scraped_at TIMESTAMP NOT NULL,
                    inventory_path TEXT,
                    tools_path TEXT,
                    vehicle_count INTEGER DEFAULT 0,
                    tools_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'success',
                    error_message TEXT,
                    cache_valid_until TIMESTAMP NOT NULL
                )
            """)

            # Job competitors table (tracks which competitors are part of which job)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_competitors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    competitor_url TEXT NOT NULL,
                    competitor_name TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    inventory_path TEXT,
                    tools_path TEXT,
                    error_message TEXT,
                    scraped_at TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scraped_url ON scraped_sites(url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_valid ON scraped_sites(cache_valid_until)")


class JobManager:
    """Manages job lifecycle and status updates"""

    def __init__(self, db: Database):
        self.db = db

    def create_job(
        self,
        job_id: str,
        client_name: str,
        client_email: str,
        competitor_urls: List[Dict[str, str]],
        data_folder: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Create a new job

        Args:
            job_id: Unique job identifier
            client_name: Client dealership name
            client_email: Email for notifications
            competitor_urls: List of {'url': str, 'name': str}
            data_folder: Path to job data folder
            metadata: Optional additional metadata

        Returns:
            job_id
        """
        total_steps = 2 + len(competitor_urls) + 2  # CSV convert + scraping + analysis + email

        with self.db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO jobs (
                    job_id, client_name, client_email, status,
                    total_steps, data_folder, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                client_name,
                client_email,
                'queued',
                total_steps,
                data_folder,
                json.dumps(metadata or {})
            ))

            # Insert competitors
            for comp in competitor_urls:
                cursor.execute("""
                    INSERT INTO job_competitors (job_id, competitor_url, competitor_name)
                    VALUES (?, ?, ?)
                """, (job_id, comp['url'], comp['name']))

        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details"""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()

            if not row:
                return None

            job = dict(row)
            job['metadata'] = json.loads(job['metadata']) if job['metadata'] else {}

            # Get competitors
            cursor.execute("""
                SELECT * FROM job_competitors WHERE job_id = ?
            """, (job_id,))
            job['competitors'] = [dict(r) for r in cursor.fetchall()]

            return job

    def update_status(
        self,
        job_id: str,
        status: str,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update job status"""
        with self.db.get_cursor() as cursor:
            updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
            params = [status]

            if current_step:
                updates.append("current_step = ?")
                params.append(current_step)

            if error_message:
                updates.append("error_message = ?")
                params.append(error_message)

            if status == 'processing' and current_step:
                updates.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")

            if status in ['completed', 'failed']:
                updates.append("completed_at = CURRENT_TIMESTAMP")

            params.append(job_id)

            cursor.execute(f"""
                UPDATE jobs SET {', '.join(updates)}
                WHERE job_id = ?
            """, params)

    def update_progress(self, job_id: str, completed_steps: int):
        """Update job progress"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE jobs
                SET completed_steps = ?,
                    progress_percentage = (completed_steps * 100) / total_steps,
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (completed_steps, job_id))

    def update_competitor_status(
        self,
        job_id: str,
        competitor_url: str,
        status: str,
        inventory_path: Optional[str] = None,
        tools_path: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update competitor scraping status"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE job_competitors
                SET status = ?,
                    inventory_path = COALESCE(?, inventory_path),
                    tools_path = COALESCE(?, tools_path),
                    error_message = ?,
                    scraped_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE scraped_at END
                WHERE job_id = ? AND competitor_url = ?
            """, (status, inventory_path, tools_path, error_message, status, job_id, competitor_url))

    def get_queued_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get queued jobs"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM jobs
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]


class CacheManager:
    """Manages scraping cache with TTL"""

    def __init__(self, db: Database, cache_ttl_days: int = 7):
        self.db = db
        self.cache_ttl_days = cache_ttl_days

    def get_cached_scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get cached scrape data if still valid

        Returns:
            Dict with inventory_path, tools_path, etc. or None if cache miss/expired
        """
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM scraped_sites
                WHERE url = ? AND cache_valid_until > CURRENT_TIMESTAMP
                AND status = 'success'
            """, (url,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def save_scrape(
        self,
        url: str,
        dealership_name: str,
        inventory_path: str,
        tools_path: str,
        vehicle_count: int = 0,
        tools_count: int = 0,
        status: str = 'success',
        error_message: Optional[str] = None
    ):
        """Save scrape results to cache"""
        cache_valid_until = datetime.now() + timedelta(days=self.cache_ttl_days)

        with self.db.get_cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO scraped_sites (
                    url, dealership_name, last_scraped_at, inventory_path,
                    tools_path, vehicle_count, tools_count, status,
                    error_message, cache_valid_until
                ) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?)
            """, (
                url, dealership_name, inventory_path, tools_path,
                vehicle_count, tools_count, status, error_message,
                cache_valid_until
            ))

    def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                DELETE FROM scraped_sites
                WHERE cache_valid_until < CURRENT_TIMESTAMP
            """)
            return cursor.rowcount


class CleanupManager:
    """Manages cleanup of old jobs and data"""

    def __init__(self, db: Database, retention_days: int = 7):
        self.db = db
        self.retention_days = retention_days

    def cleanup_old_jobs(self) -> int:
        """Delete jobs older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        with self.db.get_cursor() as cursor:
            # Get jobs to delete (with data folders)
            cursor.execute("""
                SELECT job_id, data_folder FROM jobs
                WHERE created_at < ? AND status IN ('completed', 'failed')
            """, (cutoff_date,))

            old_jobs = cursor.fetchall()

            # Delete job competitors first (foreign key)
            cursor.execute("""
                DELETE FROM job_competitors
                WHERE job_id IN (
                    SELECT job_id FROM jobs
                    WHERE created_at < ? AND status IN ('completed', 'failed')
                )
            """, (cutoff_date,))

            # Delete jobs
            cursor.execute("""
                DELETE FROM jobs
                WHERE created_at < ? AND status IN ('completed', 'failed')
            """, (cutoff_date,))

            return len(old_jobs), [dict(job) for job in old_jobs]

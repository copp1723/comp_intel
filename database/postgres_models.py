"""
PostgreSQL Database Models for Render Deployment
Uses psycopg2 instead of SQLite for shared database access
"""
import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import threading


class PostgresDatabase:
    """Thread-safe PostgreSQL database manager for Render"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize with DATABASE_URL from environment

        Args:
            database_url: PostgreSQL connection URL (defaults to env var)
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        self._local = threading.local()
        self._initialize_schema()

    def _get_connection(self):
        """Get thread-local database connection with health check"""
        # Check if we need to create a new connection
        needs_new_connection = (
            not hasattr(self._local, 'connection') or
            self._local.connection is None or
            self._local.connection.closed
        )

        # If connection exists but might be stale, verify it's alive
        if not needs_new_connection:
            try:
                # Quick health check - try to get connection status
                self._local.connection.cursor().execute("SELECT 1")
            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                # Connection is dead, mark for recreation
                needs_new_connection = True
                try:
                    self._local.connection.close()
                except:
                    pass

        # Create new connection if needed
        if needs_new_connection:
            self._local.connection = psycopg2.connect(self.database_url)
            self._local.connection.autocommit = False

        return self._local.connection

    @contextmanager
    def get_cursor(self):
        """Context manager for database operations with auto-commit and retry on connection errors"""
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                conn = self._get_connection()
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                try:
                    yield cursor
                    conn.commit()
                    return  # Success - exit
                except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                    # Connection error during transaction - rollback and retry
                    conn.rollback()
                    last_error = e
                    if cursor and not cursor.closed:
                        cursor.close()
                    # Force connection recreation on next attempt
                    try:
                        conn.close()
                    except:
                        pass
                    if hasattr(self._local, 'connection'):
                        self._local.connection = None

                    if attempt < max_retries - 1:
                        import time
                        time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        raise  # Last attempt - raise the error
                except Exception as e:
                    # Other errors (not connection related) - rollback and raise immediately
                    conn.rollback()
                    raise
                finally:
                    if cursor and not cursor.closed:
                        cursor.close()
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                # Connection error even before getting cursor - retry
                last_error = e
                if hasattr(self._local, 'connection'):
                    try:
                        self._local.connection.close()
                    except:
                        pass
                    self._local.connection = None

                if attempt < max_retries - 1:
                    import time
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    raise

        # Should never reach here, but just in case
        if last_error:
            raise last_error

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
                    metadata JSONB
                )
            """)

            # Scraped sites cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraped_sites (
                    id SERIAL PRIMARY KEY,
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

            # Job competitors table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_competitors (
                    id SERIAL PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
                    competitor_url TEXT NOT NULL,
                    competitor_name TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    inventory_path TEXT,
                    tools_path TEXT,
                    error_message TEXT,
                    scraped_at TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scraped_url ON scraped_sites(url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_valid ON scraped_sites(cache_valid_until)")


class JobManager:
    """Manages job lifecycle and status updates (PostgreSQL version)"""

    def __init__(self, db: PostgresDatabase):
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
        """Create a new job"""
        total_steps = 2 + len(competitor_urls) + 2

        with self.db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO jobs (
                    job_id, client_name, client_email, status,
                    total_steps, data_folder, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
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
                    VALUES (%s, %s, %s)
                """, (job_id, comp['url'], comp['name']))

        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details"""
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
            row = cursor.fetchone()

            if not row:
                return None

            job = dict(row)

            # Handle metadata - JSONB is auto-parsed by psycopg2 to dict
            # But if it's stored as text, we need to parse it
            if job.get('metadata'):
                if isinstance(job['metadata'], str):
                    try:
                        job['metadata'] = json.loads(job['metadata'])
                    except json.JSONDecodeError:
                        job['metadata'] = {}
                elif not isinstance(job['metadata'], dict):
                    # If it's not a string or dict, something is wrong
                    job['metadata'] = {}
            else:
                job['metadata'] = {}

            # Get competitors
            cursor.execute("""
                SELECT * FROM job_competitors WHERE job_id = %s
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
            updates = ["status = %s", "updated_at = CURRENT_TIMESTAMP"]
            params = [status]

            if current_step:
                updates.append("current_step = %s")
                params.append(current_step)

            if error_message:
                updates.append("error_message = %s")
                params.append(error_message)

            if status == 'processing' and current_step:
                updates.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")

            if status in ['completed', 'failed']:
                updates.append("completed_at = CURRENT_TIMESTAMP")

            params.append(job_id)

            cursor.execute(f"""
                UPDATE jobs SET {', '.join(updates)}
                WHERE job_id = %s
            """, params)

    def update_progress(self, job_id: str, completed_steps: int):
        """Update job progress"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE jobs
                SET completed_steps = %s,
                    progress_percentage = (completed_steps * 100.0) / NULLIF(total_steps, 0),
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_id = %s
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
                SET status = %s,
                    inventory_path = COALESCE(%s, inventory_path),
                    tools_path = COALESCE(%s, tools_path),
                    error_message = %s,
                    scraped_at = CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE scraped_at END
                WHERE job_id = %s AND competitor_url = %s
            """, (status, inventory_path, tools_path, error_message, status, job_id, competitor_url))

    def get_queued_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get queued jobs"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM jobs
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT %s
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]


class CacheManager:
    """Manages scraping cache with TTL (PostgreSQL version)"""

    def __init__(self, db: PostgresDatabase, cache_ttl_days: int = 7):
        self.db = db
        self.cache_ttl_days = cache_ttl_days

    def get_cached_scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached scrape data if still valid"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM scraped_sites
                WHERE url = %s AND cache_valid_until > CURRENT_TIMESTAMP
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
                INSERT INTO scraped_sites (
                    url, dealership_name, last_scraped_at, inventory_path,
                    tools_path, vehicle_count, tools_count, status,
                    error_message, cache_valid_until
                ) VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE SET
                    dealership_name = EXCLUDED.dealership_name,
                    last_scraped_at = CURRENT_TIMESTAMP,
                    inventory_path = EXCLUDED.inventory_path,
                    tools_path = EXCLUDED.tools_path,
                    vehicle_count = EXCLUDED.vehicle_count,
                    tools_count = EXCLUDED.tools_count,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message,
                    cache_valid_until = EXCLUDED.cache_valid_until
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
    """Manages cleanup of old jobs and data (PostgreSQL version)"""

    def __init__(self, db: PostgresDatabase, retention_days: int = 7):
        self.db = db
        self.retention_days = retention_days

    def cleanup_old_jobs(self) -> tuple[int, List[Dict]]:
        """Delete jobs older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        with self.db.get_cursor() as cursor:
            # Get jobs to delete
            cursor.execute("""
                SELECT job_id, data_folder FROM jobs
                WHERE created_at < %s AND status IN ('completed', 'failed')
            """, (cutoff_date,))

            old_jobs = [dict(row) for row in cursor.fetchall()]

            if not old_jobs:
                return 0, []

            # Delete jobs (CASCADE will delete competitors)
            cursor.execute("""
                DELETE FROM jobs
                WHERE created_at < %s AND status IN ('completed', 'failed')
            """, (cutoff_date,))

            return len(old_jobs), old_jobs

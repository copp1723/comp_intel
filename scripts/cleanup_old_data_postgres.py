#!/usr/bin/env python3
"""
PostgreSQL Cleanup Script - Remove old jobs and data
Automatically runs cleanup for jobs older than retention period
"""
import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.postgres_models import PostgresDatabase, CleanupManager, CacheManager


def cleanup_data_folders(old_jobs: list, dry_run: bool = False) -> int:
    """
    Delete data folders for old jobs

    Args:
        old_jobs: List of job dicts with 'data_folder' key
        dry_run: If True, only show what would be deleted

    Returns:
        Number of folders deleted
    """
    deleted_count = 0

    for job in old_jobs:
        data_folder = job.get('data_folder')

        if not data_folder:
            continue

        if not os.path.exists(data_folder):
            print(f"  ⚠️  Folder not found (already deleted?): {data_folder}")
            continue

        # Calculate folder size
        try:
            folder_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(data_folder)
                for filename in filenames
            )
            folder_size_mb = folder_size / (1024 * 1024)
        except Exception as e:
            print(f"  ⚠️  Error calculating size for {data_folder}: {str(e)}")
            folder_size_mb = 0

        if dry_run:
            print(f"  [DRY RUN] Would delete: {data_folder} ({folder_size_mb:.2f} MB)")
        else:
            try:
                shutil.rmtree(data_folder)
                print(f"  ✓ Deleted: {data_folder} ({folder_size_mb:.2f} MB)")
                deleted_count += 1
            except Exception as e:
                print(f"  ✗ Error deleting {data_folder}: {str(e)}")

    return deleted_count


def run_cleanup(retention_days: int = 7, dry_run: bool = False, cache_only: bool = False, jobs_only: bool = False):
    """
    Run cleanup process

    Args:
        retention_days: Number of days to retain jobs
        dry_run: If True, don't actually delete anything
        cache_only: Only cleanup cache
        jobs_only: Only cleanup jobs
    """
    print("\n" + "="*80)
    print("POSTGRES CLEANUP - OLD DATA")
    print("="*80)
    print(f"Retention period: {retention_days} days")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    try:
        # Initialize database and managers
        db = PostgresDatabase()
        cleanup_mgr = CleanupManager(db, retention_days=retention_days)
        cache_mgr = CacheManager(db)

        # Cleanup jobs
        if not cache_only:
            print("🗑️  CLEANING UP OLD JOBS")
            print("-" * 80)

            count, old_jobs = cleanup_mgr.cleanup_old_jobs()

            if count == 0:
                print("  ✓ No old jobs to cleanup")
            else:
                if dry_run:
                    print(f"  [DRY RUN] Would delete {count} job(s) from database")
                else:
                    print(f"  ✓ Deleted {count} job(s) from database")

                # Cleanup data folders
                if old_jobs:
                    print(f"\n  Cleaning up data folders...")
                    deleted = cleanup_data_folders(old_jobs, dry_run=dry_run)

                    if not dry_run:
                        print(f"  ✓ Deleted {deleted}/{len(old_jobs)} data folders")

            print()

        # Cleanup expired cache
        if not jobs_only:
            print("🗑️  CLEANING UP EXPIRED CACHE")
            print("-" * 80)

            if dry_run:
                # Count expired without deleting
                with db.get_cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM scraped_sites
                        WHERE cache_valid_until < CURRENT_TIMESTAMP
                    """)
                    result = cursor.fetchone()
                    count = result['count'] if result else 0

                if count == 0:
                    print("  ✓ No expired cache entries")
                else:
                    print(f"  [DRY RUN] Would delete {count} expired cache entry/entries")
            else:
                count = cache_mgr.cleanup_expired()

                if count == 0:
                    print("  ✓ No expired cache entries")
                else:
                    print(f"  ✓ Deleted {count} expired cache entry/entries")

            print()

        # Summary
        print("="*80)
        if dry_run:
            print("DRY RUN COMPLETE - No actual deletions performed")
        else:
            print("CLEANUP COMPLETE")
        print("="*80 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ Error during cleanup: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point for command-line usage"""
    parser = argparse.ArgumentParser(
        description="Cleanup old jobs and data files (PostgreSQL)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Cleanup jobs older than 7 days (default)
  python cleanup_old_data_postgres.py

  # Cleanup jobs older than 30 days
  python cleanup_old_data_postgres.py --retention-days 30

  # Dry run (show what would be deleted without deleting)
  python cleanup_old_data_postgres.py --dry-run

  # Cleanup expired cache only
  python cleanup_old_data_postgres.py --cache-only

  # Cleanup jobs only
  python cleanup_old_data_postgres.py --jobs-only
        """
    )

    parser.add_argument(
        '--retention-days',
        type=int,
        default=7,
        help='Number of days to retain completed/failed jobs (default: 7)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )

    parser.add_argument(
        '--cache-only',
        action='store_true',
        help='Only cleanup expired cache entries, skip jobs'
    )

    parser.add_argument(
        '--jobs-only',
        action='store_true',
        help='Only cleanup old jobs, skip cache'
    )

    args = parser.parse_args()

    success = run_cleanup(
        retention_days=args.retention_days,
        dry_run=args.dry_run,
        cache_only=args.cache_only,
        jobs_only=args.jobs_only
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

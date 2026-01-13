#!/usr/bin/env python3
"""
Cleanup Script - Remove old jobs and data
Configurable retention period (default: 7 days)
"""
import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import Database, CleanupManager, CacheManager


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
        folder_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, dirnames, filenames in os.walk(data_folder)
            for filename in filenames
        )
        folder_size_mb = folder_size / (1024 * 1024)

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


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Cleanup old jobs and data files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Cleanup jobs older than 7 days (default)
  python cleanup_old_data.py

  # Cleanup jobs older than 30 days
  python cleanup_old_data.py --retention-days 30

  # Dry run (show what would be deleted without deleting)
  python cleanup_old_data.py --dry-run

  # Custom database path
  python cleanup_old_data.py --db-path /path/to/database.db

  # Cleanup expired cache only
  python cleanup_old_data.py --cache-only
        """
    )

    parser.add_argument(
        '--retention-days',
        type=int,
        default=7,
        help='Number of days to retain completed/failed jobs (default: 7)'
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default='data/database.db',
        help='Path to SQLite database (default: data/database.db)'
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

    # Validate database exists
    if not os.path.exists(args.db_path):
        print(f"❌ Database not found: {args.db_path}")
        print("   No cleanup needed (database doesn't exist yet)")
        sys.exit(0)

    print("\n" + "="*80)
    print("CLEANUP OLD DATA")
    print("="*80)
    print(f"Retention period: {args.retention_days} days")
    print(f"Database: {args.db_path}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("="*80 + "\n")

    # Initialize database and managers
    db = Database(args.db_path)
    cleanup_mgr = CleanupManager(db, retention_days=args.retention_days)
    cache_mgr = CacheManager(db)

    total_freed_mb = 0

    # Cleanup jobs
    if not args.cache_only:
        print("🗑️  CLEANING UP OLD JOBS")
        print("-" * 80)

        count, old_jobs = cleanup_mgr.cleanup_old_jobs()

        if count == 0:
            print("  ✓ No old jobs to cleanup")
        else:
            if args.dry_run:
                print(f"  [DRY RUN] Would delete {count} job(s) from database")
            else:
                print(f"  ✓ Deleted {count} job(s) from database")

            # Cleanup data folders
            if old_jobs:
                print(f"\n  Cleaning up data folders...")
                deleted = cleanup_data_folders(old_jobs, dry_run=args.dry_run)

                if not args.dry_run:
                    print(f"  ✓ Deleted {deleted}/{len(old_jobs)} data folders")

        print()

    # Cleanup expired cache
    if not args.jobs_only:
        print("🗑️  CLEANING UP EXPIRED CACHE")
        print("-" * 80)

        if args.dry_run:
            # Count expired without deleting
            with db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM scraped_sites
                    WHERE cache_valid_until < CURRENT_TIMESTAMP
                """)
                count = cursor.fetchone()['count']

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
    if args.dry_run:
        print("DRY RUN COMPLETE - No actual deletions performed")
    else:
        print("CLEANUP COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

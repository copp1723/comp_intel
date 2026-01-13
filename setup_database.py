#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script
Creates all required database tables

Usage:
    python setup_database.py              # Use DATABASE_URL from .env
    python setup_database.py --db-url postgresql://...  # Custom database URL
    python setup_database.py --verify     # Verify tables after creation
"""
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

database_url = os.getenv("DATABASE_URL")

def setup_postgresql(database_url: str):
    """Setup PostgreSQL database tables"""
    print("Setting up PostgreSQL database...")
    print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")

    try:
        from database.postgres_models import PostgresDatabase

        # Initialize database (this creates all tables)
        db = PostgresDatabase(database_url)

        print("\n✅ SUCCESS: PostgreSQL tables created!")
        print("\nTables created:")
        print("  1. jobs - Job queue and tracking")
        print("  2. scraped_sites - Competitor scraping cache")
        print("  3. job_competitors - Job-specific competitor tracking")
        print("\nIndexes created:")
        print("  - idx_jobs_status (jobs.status)")
        print("  - idx_jobs_created (jobs.created_at)")
        print("  - idx_scraped_url (scraped_sites.url)")
        print("  - idx_cache_valid (scraped_sites.cache_valid_until)")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: Failed to create PostgreSQL tables")
        print(f"Error: {str(e)}")
        return False


def verify_tables(database_url: str):
    """Verify PostgreSQL tables were created"""
    try:
        import psycopg2

        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Query for tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        tables = [row[0] for row in cursor.fetchall()]

        print("\n📊 Verification:")
        print(f"Tables found: {len(tables)}")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  ✓ {table} ({count} rows)")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n⚠️  Could not verify tables: {str(e)}")


def main():

    print("="*80)
    print("POSTGRESQL DATABASE SETUP")
    print("="*80)
    print()


    if not database_url:
        return None 

    success = setup_postgresql(database_url)

    if success:
        verify_tables(database_url)

        print("✅ DATABASE SETUP COMPLETE")
        print("="*80)


if __name__ == "__main__":
    main()

"""
Job Orchestrator for PostgreSQL
Coordinates the entire workflow: JSON data → Scraping → Analysis → Email notification
"""
import os
import sys
import json
import time
import threading
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import subprocess
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import PostgreSQL models
from database.postgres_models import PostgresDatabase, JobManager, CacheManager

# Get logger (will use the logger configured by worker.py)
logger = logging.getLogger(__name__)


class JobProcessorPostgres:
    """
    Orchestrates complete job workflow with retry logic and caching
    Uses PostgreSQL for production deployment
    """

    def __init__(
        self,
        database_url: str = None,
        cache_ttl_days: int = 7,
        scraper_max_retries: int = 2,
        email_max_retries: int = 3
    ):
        """
        Initialize job processor with PostgreSQL

        Args:
            database_url: PostgreSQL connection URL (defaults to DATABASE_URL env var)
            cache_ttl_days: Cache TTL in days (default: 7)
            scraper_max_retries: Max retries per competitor (default: 2)
            email_max_retries: Max email send retries (default: 3)
        """
        # Use PostgreSQL
        self.db = PostgresDatabase(database_url)
        self.job_mgr = JobManager(self.db)
        self.cache_mgr = CacheManager(self.db, cache_ttl_days=cache_ttl_days)

        self.scraper_max_retries = scraper_max_retries
        self.email_max_retries = email_max_retries

        # Worker thread (not used in Render - separate service)
        self._worker_thread = None
        self._stop_worker = False

    def submit_job(
        self,
        client_name: str,
        client_email: str,
        inventory_csv_path: str,
        tools_csv_path: str,
        competitor_urls: List[Dict[str, str]],  # [{'url': str, 'name': str}, ...]
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Submit a new job for processing

        Args:
            client_name: Client dealership name
            client_email: Email for notifications
            inventory_csv_path: Path to inventory CSV
            tools_csv_path: Path to tools CSV
            competitor_urls: List of competitor URLs and names
            metadata: Optional metadata

        Returns:
            job_id
        """
        # Generate job ID
        job_id = f"job_{uuid.uuid4().hex[:12]}_{int(time.time())}"

        # Create data folder
        data_folder = f"data/jobs/{job_id}"
        Path(data_folder).mkdir(parents=True, exist_ok=True)

        # Store CSV paths in metadata
        full_metadata = {
            **(metadata or {}),
            'inventory_csv': inventory_csv_path,
            'tools_csv': tools_csv_path,
            'submitted_at': datetime.now().isoformat()
        }

        # Create job in database
        self.job_mgr.create_job(
            job_id=job_id,
            client_name=client_name,
            client_email=client_email,
            competitor_urls=competitor_urls,
            data_folder=data_folder,
            metadata=full_metadata
        )

        print(f"✅ Job submitted: {job_id}")
        print(f"   Client: {client_name}")
        print(f"   Competitors: {len(competitor_urls)}")
        print(f"   Data folder: {data_folder}")

        return job_id

    def process_job(self, job_id: str) -> bool:
        """
        Process a single job through all steps

        Args:
            job_id: Job ID to process

        Returns:
            True if successful, False otherwise
        """
        print(f"\n{'='*80}")
        print(f"PROCESSING JOB: {job_id}")
        print(f"{'='*80}\n")

        try:
            # Get job details
            job = self.job_mgr.get_job(job_id)
            if not job:
                print(f"❌ Job not found: {job_id}")
                return False

            # Update status to processing
            self.job_mgr.update_status(job_id, 'processing', current_step='Starting')

            client_name = job['client_name']
            client_email = job['client_email']
            data_folder = job['data_folder']
            metadata = job['metadata']

            # Handle both old and new metadata formats
            # Old format: csv1_json, csv2_json
            # New format: inventory_json, tools_json
            if 'inventory_json' not in metadata and 'csv1_json' in metadata:
                # Old format - need to determine which is which
                # Assume csv1_json is inventory and csv2_json is tools (should be fine for old jobs)
                print(f"  ℹ Converting old metadata format to new format")
                metadata['inventory_json'] = metadata.get('csv1_json', '[]')
                metadata['tools_json'] = metadata.get('csv2_json', '[]')

            # Create data folder if not set (for jobs from frontend)
            if not data_folder:
                data_folder = f"data/jobs/{job_id}"
                os.makedirs(data_folder, exist_ok=True)
                print(f"  ℹ Created data folder: {data_folder}")

            completed_steps = 0

            # ========== STEP 1: Save client data to JSON files ==========
            print(f"\n[Step 1/{job['total_steps']}] Saving client data...")
            self.job_mgr.update_status(job_id, 'processing', current_step='Saving client data')

            client_inventory_path = f"{data_folder}/client_{client_name}_{int(time.time())}_inventory.json"
            client_tools_path = f"{data_folder}/client_{client_name}_{int(time.time())}_tools.json"

            # Save inventory JSON (already in JSON format from frontend)
            try:
                # Verify metadata has the required fields
                if 'inventory_json' not in metadata:
                    raise KeyError(f"'inventory_json' not found in metadata. Available keys: {list(metadata.keys())}")

                with open(client_inventory_path, 'w', encoding='utf-8') as f:
                    f.write(metadata['inventory_json'])

                # Count vehicles
                inventory_data = json.loads(metadata['inventory_json'])
                client_vehicle_count = len(inventory_data) if isinstance(inventory_data, list) else 0
                print(f"  ✓ Inventory saved: {client_vehicle_count} vehicles")

            except Exception as e:
                error_msg = f"Inventory data error: {str(e)}"
                print(f"  ❌ {error_msg}")
                print(f"  DEBUG: metadata type = {type(metadata)}")
                print(f"  DEBUG: metadata keys = {list(metadata.keys()) if isinstance(metadata, dict) else 'N/A'}")
                self.job_mgr.update_status(job_id, 'failed', error_message=error_msg)
                return False

            # Save tools JSON (already in JSON format from frontend)
            try:
                with open(client_tools_path, 'w', encoding='utf-8') as f:
                    f.write(metadata['tools_json'])

                # Count tools
                tools_data = json.loads(metadata['tools_json'])
                client_tools_count = len(tools_data) if isinstance(tools_data, list) else 0
                print(f"  ✓ Tools saved: {client_tools_count} tools")

            except Exception as e:
                self.job_mgr.update_status(job_id, 'failed', error_message=f"Tools data error: {str(e)}")
                return False

            completed_steps += 1
            self.job_mgr.update_progress(job_id, completed_steps)

            # ========== STEP 2: Scrape Competitors ==========
            print(f"\n[Step 2-{1+len(job['competitors'])}] Scraping competitors...")

            competitors_data = []
            failed_competitors = 0

            for i, comp in enumerate(job['competitors'], 1):
                comp_url = comp['competitor_url']
                comp_name = comp['competitor_name']

                print(f"\n  [{i}/{len(job['competitors'])}] Processing: {comp_name}")
                print(f"      URL: {comp_url}")

                # Check cache first
                cached = self.cache_mgr.get_cached_scrape(comp_url)

                if cached:
                    # Validate that cached files still exist
                    if os.path.exists(cached['inventory_path']) and os.path.exists(cached['tools_path']):
                        print(f"      ✓ Cache hit! Using cached data")
                        print(f"        Last scraped: {cached['last_scraped_at']}")
                        print(f"        Vehicles: {cached['vehicle_count']}, Tools: {cached['tools_count']}")

                        self.job_mgr.update_competitor_status(
                            job_id=job_id,
                            competitor_url=comp_url,
                            status='completed',
                            inventory_path=cached['inventory_path'],
                            tools_path=cached['tools_path']
                        )

                        competitors_data.append({
                            'name': comp_name,
                            'url': comp_url,
                            'inventory_path': cached['inventory_path'],
                            'tools_path': cached['tools_path']
                        })

                        completed_steps += 1
                        self.job_mgr.update_progress(job_id, completed_steps)
                        continue
                    else:
                        print(f"      ⚠️  Cache hit but files missing - invalidating cache and rescraping...")
                        cached = None  # Treat as cache miss

                # Cache miss - need to scrape
                print(f"      ⚠️  Cache miss - scraping...")

                scrape_success = False
                for attempt in range(1, self.scraper_max_retries + 1):
                    print(f"        Attempt {attempt}/{self.scraper_max_retries}...")

                    try:
                        inv_path, tools_path, veh_count, tools_count = self._run_scraper(
                            url=comp_url,
                            comp_name=comp_name,
                            data_folder=data_folder
                        )

                        # Success!
                        print(f"        ✓ Scrape successful")
                        print(f"          Vehicles: {veh_count}, Tools: {tools_count}")

                        # Save to cache
                        self.cache_mgr.save_scrape(
                            url=comp_url,
                            dealership_name=comp_name,
                            inventory_path=inv_path,
                            tools_path=tools_path,
                            vehicle_count=veh_count,
                            tools_count=tools_count,
                            status='success'
                        )

                        self.job_mgr.update_competitor_status(
                            job_id=job_id,
                            competitor_url=comp_url,
                            status='completed',
                            inventory_path=inv_path,
                            tools_path=tools_path
                        )

                        competitors_data.append({
                            'name': comp_name,
                            'url': comp_url,
                            'inventory_path': inv_path,
                            'tools_path': tools_path
                        })

                        scrape_success = True
                        break

                    except Exception as e:
                        print(f"        ✗ Attempt {attempt} failed: {str(e)}")

                        if attempt < self.scraper_max_retries:
                            print(f"        Retrying...")
                            time.sleep(2)
                        else:
                            print(f"        ✗ All retries exhausted")

                if not scrape_success:
                    failed_competitors += 1
                    self.job_mgr.update_competitor_status(
                        job_id=job_id,
                        competitor_url=comp_url,
                        status='failed',
                        error_message=f"Scraping failed after {self.scraper_max_retries} retries"
                    )

                    # Check abort condition: if 2+ competitors fail, abort
                    if failed_competitors >= 2:
                        error_msg = f"Aborting: {failed_competitors} competitors failed (threshold: 2)"
                        print(f"\n❌ {error_msg}")

                        # Mark remaining competitors as 'aborted'
                        for remaining_comp in job['competitors'][i:]:
                            self.job_mgr.update_competitor_status(
                                job_id=job_id,
                                competitor_url=remaining_comp['competitor_url'],
                                status='aborted',
                                error_message='Job aborted due to multiple failures'
                            )

                        self.job_mgr.update_status(job_id, 'failed', error_message=error_msg)
                        return False

                completed_steps += 1
                self.job_mgr.update_progress(job_id, completed_steps)

            # Check if we have at least 1 successful competitor
            if len(competitors_data) == 0:
                error_msg = "No competitors scraped successfully"
                print(f"\n❌ {error_msg}")
                self.job_mgr.update_status(job_id, 'failed', error_message=error_msg)
                return False

            print(f"\n  ✓ Successfully scraped {len(competitors_data)}/{len(job['competitors'])} competitors")

            # ========== STEP 3: Run Analysis ==========
            analysis_step = completed_steps + 1
            print(f"\n[Step {analysis_step}/{job['total_steps']}] Running market analysis...")
            self.job_mgr.update_status(job_id, 'processing', current_step='Running analysis')

            analysis_output = f"{data_folder}/analysis_{int(time.time())}.txt"

            try:
                self._run_analysis(
                    client_inventory=client_inventory_path,
                    client_tools=client_tools_path,
                    client_name=client_name,
                    competitors_data=competitors_data,
                    output_path=analysis_output
                )
                print(f"  ✓ Analysis complete: {analysis_output}")

            except Exception as e:
                error_msg = f"Analysis failed: {str(e)}"
                print(f"  ✗ {error_msg}")
                self.job_mgr.update_status(job_id, 'failed', error_message=error_msg)
                return False

            completed_steps += 1
            self.job_mgr.update_progress(job_id, completed_steps)

            # ========== STEP 4: Send Email ==========
            email_step = completed_steps + 1
            print(f"\n[Step {email_step}/{job['total_steps']}] Sending email notification...")
            self.job_mgr.update_status(job_id, 'processing', current_step='Sending email')

            email_success = False
            for attempt in range(1, self.email_max_retries + 1):
                print(f"  Attempt {attempt}/{self.email_max_retries}...")

                try:
                    self._send_email(
                        to_email=client_email,
                        client_name=client_name,
                        analysis_file=analysis_output,
                        vehicle_count=client_vehicle_count,
                        tools_count=client_tools_count,
                        competitors_count=len(competitors_data)
                    )

                    print(f"  ✓ Email sent successfully to {client_email}")
                    email_success = True
                    break

                except Exception as e:
                    print(f"  ✗ Attempt {attempt} failed: {str(e)}")

                    if attempt < self.email_max_retries:
                        print(f"  Retrying in 5 seconds...")
                        time.sleep(5)

            if not email_success:
                error_msg = f"Email failed after {self.email_max_retries} retries"
                print(f"\n❌ {error_msg}")
                self.job_mgr.update_status(job_id, 'failed', error_message=error_msg)
                return False

            completed_steps += 1
            self.job_mgr.update_progress(job_id, completed_steps)

            # ========== STEP 5: Mark Job Complete ==========
            final_step = completed_steps + 1
            print(f"\n[Step {final_step}/{job['total_steps']}] Finalizing job...")
            self.job_mgr.update_status(job_id, 'completed', current_step='Completed')

            completed_steps += 1
            self.job_mgr.update_progress(job_id, completed_steps)

            print(f"\n{'='*80}")
            print(f"✅ JOB COMPLETED: {job_id}")
            print(f"{'='*80}\n")

            return True

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"\n❌ {error_msg}")
            import traceback
            traceback.print_exc()
            self.job_mgr.update_status(job_id, 'failed', error_message=error_msg)
            return False

    def _run_scraper(
        self,
        url: str,
        comp_name: str,
        data_folder: str
    ) -> Tuple[str, str, int, int]:
        """
        Run scraper for a competitor URL

        Returns:
            (inventory_path, tools_path, vehicle_count, tools_count)
        """
        timestamp = int(time.time())
        output_prefix = f"{comp_name}_{timestamp}"

        # Prepare environment variables for scraper
        scraper_env = os.environ.copy()
        scraper_env["SCRAPER_DOMAIN"] = url

        # Run scraper (no CLI arguments - all config via environment)
        # Use -u flag to force unbuffered output so we see logs immediately
        cmd = [
            sys.executable,
            "-u",  # Unbuffered output
            "inventory_tool_scraper.py"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
            env=scraper_env
        )

        # Always log scraper output for debugging
        print(f"\n  📋 SCRAPER OUTPUT:")
        print(f"  Return Code: {result.returncode}")

        # Also log to logger so it gets written to file
        logger.info(f"Scraper output for {comp_name}:")
        logger.info(f"Return Code: {result.returncode}")

        if result.stdout:
            print(f"  STDOUT ({len(result.stdout)} chars):")
            print(result.stdout)  # Show ALL output, not just last 2000 chars
            # Log to file as well
            for line in result.stdout.splitlines():
                logger.info(f"[SCRAPER] {line}")
        else:
            print(f"  STDOUT: (empty)")
            logger.info("[SCRAPER] STDOUT: (empty)")

        if result.stderr:
            print(f"  STDERR ({len(result.stderr)} chars):")
            print(result.stderr)  # Show ALL output
            # Log to file as well
            for line in result.stderr.splitlines():
                logger.info(f"[SCRAPER] {line}")
        else:
            print(f"  STDERR: (empty)")
            logger.info("[SCRAPER] STDERR: (empty)")

        if result.returncode != 0:
            raise Exception(f"Scraper failed with exit code {result.returncode}. See output above.")

        # Move output files to job folder (scraper always outputs to fixed names)
        inv_src = "output/inventory.json"
        tools_src = "output/tools.json"

        inv_dest = f"{data_folder}/{output_prefix}_inventory.json"
        tools_dest = f"{data_folder}/{output_prefix}_tools.json"

        # Check if files exist before trying to move them
        if not os.path.exists(inv_src):
            print(f"\n  ❌ ERROR: Inventory file not created by scraper")
            print(f"  Expected: {inv_src}")
            print(f"  Scraper completed with exit code 0 but didn't create output files!")
            raise Exception(f"Inventory file not found: {inv_src}. Scraper may have failed silently.")
        if not os.path.exists(tools_src):
            raise Exception(f"Tools file not found: {tools_src}")

        shutil.move(inv_src, inv_dest)
        shutil.move(tools_src, tools_dest)

        # Count vehicles and tools
        with open(inv_dest, 'r') as f:
            inventory = json.load(f)
            veh_count = len(inventory) if isinstance(inventory, list) else 0

        with open(tools_dest, 'r') as f:
            tools = json.load(f)
            # Support both is_present (new) and isPresent (old) formats
            tools_count = sum(1 for t in tools if t.get('is_present', t.get('isPresent', False))) if isinstance(tools, list) else 0

        return inv_dest, tools_dest, veh_count, tools_count

    def _run_analysis(
        self,
        client_inventory: str,
        client_tools: str,
        client_name: str,
        competitors_data: List[Dict],
        output_path: str
    ):
        """Run market analysis using market_comparator.py"""
        # Prepare file list for market_comparator
        # Pass absolute paths directly - market_comparator supports both user_ and client_ prefixes
        files = [
            os.path.abspath(client_inventory),
            os.path.abspath(client_tools)
        ]

        for comp in competitors_data:
            files.append(os.path.abspath(comp['inventory_path']))
            files.append(os.path.abspath(comp['tools_path']))

        # Run market_comparator
        cmd = [
            sys.executable,
            "dealership_scraper/analyses/market_comparator.py"
        ] + files

        print(f"\n  📂 Running analysis with {len(files)} files:")
        for f in files:
            print(f"     - {os.path.basename(f)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        # Always log analysis output for debugging
        print(f"\n  📋 ANALYSIS OUTPUT:")
        print(f"  Return Code: {result.returncode}")
        if result.stdout:
            print(f"  STDOUT ({len(result.stdout)} chars):")
            print(result.stdout)
        else:
            print(f"  STDOUT: (empty)")
        if result.stderr:
            print(f"  STDERR ({len(result.stderr)} chars):")
            print(result.stderr)
        else:
            print(f"  STDERR: (empty)")

        if result.returncode != 0:
            raise Exception(f"Analysis failed with exit code {result.returncode}. See output above.")

        # Move email.txt to output_path
        if os.path.exists("email.txt"):
            shutil.move("email.txt", output_path)
        else:
            raise Exception("Analysis did not generate email.txt")

    def _send_email(
        self,
        to_email: str,
        client_name: str,
        analysis_file: str,
        vehicle_count: int,
        tools_count: int,
        competitors_count: int
    ):
        """Send email with analysis results"""
        # Read analysis
        with open(analysis_file, 'r') as f:
            analysis_text = f.read()

        # Import email notification
        from dealership_scraper.notification.email_notification import send_single_email

        subject = f"Market Analysis Report for {client_name}"

        success = send_single_email(
            to_address=to_email,
            subject=subject,
            message=analysis_text
        )

        if not success:
            raise Exception("Email send failed")

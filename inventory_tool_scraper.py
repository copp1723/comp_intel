#!/usr/bin/env python3
"""
Dealership Scraper - Clean, modular implementation
Extracts inventory and detects tools from car dealership websites
"""
import os
import sys
import json
import asyncio
import random
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from crawl4ai import AsyncWebCrawler, AsyncUrlSeeder, CrawlerRunConfig, CacheMode, BrowserConfig, SeedingConfig
from dealership_scraper.models import ToolType
from dealership_scraper.utils.url_classifier import classify_urls
from dealership_scraper.detectors import ToolDetector
from dealership_scraper.extractors import InventoryExtractor

# Configure logging to write to both file and console
def setup_logging():
    """Setup logging to write to both file and stderr"""
    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/scraper_{timestamp}.log"

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

    # Add console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
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


class DealershipScraper:
    """
    Main scraper orchestrator

    Note: When detect_tools=True, the scraper will ALWAYS check some VDP and SRP pages
    for payment detection (tools #7 and #8), even if extract_inventory=False.
    This ensures accurate tool detection.
    """

    def __init__(
        self,
        domain: str,
        api_key: str,
        extract_inventory: bool = True,
        detect_tools: bool = True,
        max_vdp_urls: int = 100,
        max_srp_urls: int = 50,
        max_finance_urls: int = 50,
        detection_strictness: str = "lenient",
        enable_inventory_pagination: bool = False,
        max_pages_per_url: int = 40,
        headless: bool = True,
        enable_parallel_processing: bool = False,
        max_parallel_workers: int = 3,
        proxy_config: Optional[Dict[str, str]] = None
    ):
        """
        Initialize scraper

        Args:
            domain: Website domain to scrape
            api_key: OpenAI API key
            extract_inventory: Whether to extract vehicle inventory
            detect_tools: Whether to detect dealership tools
            max_vdp_urls: Max VDP (Vehicle Detail Page) URLs to process (default: 100)
            max_srp_urls: Max SRP (Search Results Page) URLs to process (default: 50)
            max_finance_urls: Max finance URLs to process
            detection_strictness: Tool detection mode - "strict" or "lenient" (default: "lenient")
                - "strict": Requires definitive proof, visible payments, actual form elements
                - "lenient": More practical, accepts tools behind buttons/modals, flexible requirements
            enable_inventory_pagination: Enable pagination for SRP pages in inventory extraction (default: False)
                                        VDP pages never use pagination regardless of this setting
            max_pages_per_url: Maximum pages to crawl per URL when pagination is enabled (default: 40)
            headless: Run browser in headless mode (default: True). Set to False to see browser
            enable_parallel_processing: Process URLs in parallel for faster extraction (default: False)
            max_parallel_workers: Number of parallel workers (default: 3)
        """
        self.domain = domain
        self.api_key = api_key
        self.extract_inventory = extract_inventory
        self.detect_tools = detect_tools
        self.max_vdp_urls = max_vdp_urls
        self.max_srp_urls = max_srp_urls
        self.max_finance_urls = max_finance_urls
        self.detection_strictness = detection_strictness
        self.enable_inventory_pagination = enable_inventory_pagination
        self.max_pages_per_url = max_pages_per_url
        self.headless = headless
        self.enable_parallel_processing = enable_parallel_processing
        self.max_parallel_workers = max_parallel_workers

        # Initialize modules
        self.tool_detector = ToolDetector(
            api_key=api_key,
            strictness=detection_strictness,
            enable_parallel=enable_parallel_processing,
            max_workers=max_parallel_workers
        )
        self.inventory_extractor = InventoryExtractor(
            api_key=api_key,
            enrich_with_vin=True,
            enable_pagination=enable_inventory_pagination,
            max_pages_per_url=max_pages_per_url,
            headless=headless,
            enable_parallel=enable_parallel_processing,
            max_workers=max_parallel_workers,
            proxy_config=proxy_config
        )

    def print_config(self):
        """Print configuration"""
        print("\n" + "="*80)
        print("DEALERSHIP SCRAPER")
        print("="*80)
        print(f"Domain:              {self.domain}")
        print(f"Browser Mode:        {'HEADLESS' if self.headless else 'VISIBLE (headless=False)'}")
        print(f"Extract Inventory:   {'YES' if self.extract_inventory else 'NO'}")
        print(f"Detect Tools:        {'YES' if self.detect_tools else 'NO'}")
        if self.extract_inventory:
            print(f"Max VDP URLs:        {self.max_vdp_urls}")
            print(f"Max SRP URLs:        {self.max_srp_urls}")
            print(f"Inventory Pagination: {'ENABLED' if self.enable_inventory_pagination else 'DISABLED'}")
            if self.enable_inventory_pagination:
                print(f"Max Pages Per URL:   {self.max_pages_per_url}")
            print(f"Parallel Processing: {'ENABLED' if self.enable_parallel_processing else 'DISABLED'}")
            if self.enable_parallel_processing:
                print(f"Parallel Workers:    {self.max_parallel_workers}")
        if self.detect_tools:
            print(f"Max Finance URLs:    {self.max_finance_urls}")
            print(f"Detection Strictness: {self.detection_strictness.upper()}")
        print("="*80 + "\n")

    async def seed_urls(self) -> list:
        """Phase 1: Seed URLs from domain"""
        print("PHASE 1: Seeding URLs from domain...")

        all_urls = set()
        sources_used = []
        clean_domain = self.domain.replace('https://', '').replace('http://', '').rstrip('/')

        # Strategy 1: Use AsyncUrlSeeder (sitemap + Common Crawl)
        print("  Strategy 1: Using AsyncUrlSeeder (sitemap + Common Crawl)...")
        try:
            seeder = AsyncUrlSeeder()
            config = SeedingConfig(
                source="sitemap+cc",  # sitemap + common crawl
                max_urls=500,
                filter_nonsense_urls=True
            )

            url_dicts = await seeder.urls(self.domain, config)
            seeder_urls = [item['url'] for item in url_dicts if 'url' in item]

            if len(seeder_urls) > 0:
                all_urls.update(seeder_urls)
                sources_used.append("sitemap+cc")
                print(f"  ✓ Found {len(seeder_urls)} URLs from sitemap/Common Crawl")
            else:
                print(f"  ⚠️  No URLs found from sitemap/Common Crawl")
        except Exception as e:
            print(f"  ✗ AsyncUrlSeeder failed: {str(e)}")

        # Strategy 2: Crawl homepage (only if we have < 50 URLs from Strategy 1)
        if len(all_urls) < 50:
            print(f"  Strategy 2: Crawling homepage (found {len(all_urls)} URLs so far, need more)...")
            try:
                homepage_urls = await self.discover_urls_from_homepage()
                if len(homepage_urls) > 0:
                    all_urls.update(homepage_urls)
                    sources_used.append("homepage+deep")
                    print(f"  ✓ Found {len(homepage_urls)} URLs from homepage crawl")
                else:
                    print(f"  ⚠️  No URLs found from homepage crawl")
            except Exception as e:
                print(f"  ✗ Homepage crawl failed: {str(e)}")

        # Error if no URLs found from both strategies
        if len(all_urls) == 0:
            error_msg = f"❌ Failed to discover any URLs from {clean_domain} - both strategies failed"
            if sources_used:
                error_msg += f" (tried: {', '.join(sources_used)})"
            raise RuntimeError(error_msg)

        # Save results
        urls = sorted(list(all_urls))
        os.makedirs("output", exist_ok=True)
        with open("output/all_urls.txt", "w", encoding="utf-8") as f:
            f.write(f"# All URLs scraped from {clean_domain}\n")
            f.write(f"# Total: {len(urls)} URLs\n")
            f.write(f"# Sources: {', '.join(sources_used)}\n\n")
            for url in urls:
                f.write(f"{url}\n")

        print(f"\n✓ Seeded {len(urls)} URLs (sources: {', '.join(sources_used)})")
        print(f"✓ Saved to: output/all_urls.txt\n")
        return urls



    async def discover_urls_from_homepage(self) -> list:
        """Discover URLs by crawling homepage and extracting links (with 1-level deep crawl)"""
        # Properly format homepage URL
        clean_domain = self.domain.replace('https://', '').replace('http://', '').rstrip('/')
        homepage = f"https://{clean_domain}"

        print(f"    Level 0: Crawling homepage: {homepage}")
        browser_config = BrowserConfig(headless=self.headless, verbose=False)

        all_discovered_urls = set()

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Level 0: Crawl homepage
                result = await crawler.arun(
                    homepage,
                    config=CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        wait_until="domcontentloaded",
                        page_timeout=60000,
                        wait_for_images=False
                    )
                )

                if result.success and result.links:
                    # Extract internal links from homepage
                    level_0_links = []
                    for link_info in result.links.get('internal', []):
                        url = link_info.get('href')
                        if url and url not in all_discovered_urls:
                            all_discovered_urls.add(url)
                            level_0_links.append(url)

                    print(f"    ✓ Level 0: Found {len(level_0_links)} links from homepage")

                    # Level 1: Deep crawl - visit key pages that might link to inventory
                    # Focus on pages likely to have inventory links
                    priority_keywords = ['inventory', 'vehicles', 'new', 'used', 'certified', 'cpo', 'cars', 'trucks', 'suv']

                    level_1_candidates = []
                    for url in level_0_links:
                        url_lower = url.lower()
                        # Check if URL contains priority keywords and is not too deep
                        if any(keyword in url_lower for keyword in priority_keywords):
                            # Avoid very deep URLs (max 2 path segments after domain)
                            path_segments = url.replace('https://', '').replace('http://', '').split('/')[1:]
                            if len(path_segments) <= 2:
                                level_1_candidates.append(url)

                    if level_1_candidates:
                        print(f"    Level 1: Deep crawling {len(level_1_candidates)} priority pages...")

                        for idx, page_url in enumerate(level_1_candidates, 1):
                            try:
                                # Show truncated URL for readability
                                display_url = page_url if len(page_url) <= 60 else page_url[:57] + "..."
                                print(f"      [{idx}/{len(level_1_candidates)}] {display_url}", end='', flush=True)

                                page_result = await crawler.arun(
                                    page_url,
                                    config=CrawlerRunConfig(
                                        cache_mode=CacheMode.BYPASS,
                                        wait_until="domcontentloaded",
                                        page_timeout=30000,  # Shorter timeout for level 1
                                        wait_for_images=False
                                    )
                                )

                                if page_result.success and page_result.links:
                                    new_links = 0
                                    for link_info in page_result.links.get('internal', []):
                                        url = link_info.get('href')
                                        if url and url not in all_discovered_urls:
                                            all_discovered_urls.add(url)
                                            new_links += 1

                                    print(f" → +{new_links} links")
                                else:
                                    print(f" → 0 links")

                            except Exception as e:
                                print(f" → Error: {str(e)[:50]}")
                                continue

                        print(f"    ✓ Level 1: Deep crawl complete")

                    discovered_list = list(all_discovered_urls)
                    print(f"    ✓ Total discovered: {len(discovered_list)} URLs")
                    return discovered_list[:500]  # Limit to 500 URLs

                elif result.success:
                    print(f"    ⚠️  Homepage loaded but no links found")
                else:
                    print(f"    ✗ Homepage failed to load")
        except Exception as e:
            print(f"    ✗ Homepage crawl error: {str(e)[:150]}")

        return []

    async def classify_urls_phase(self, urls: list) -> Dict[str, list]:
        """Phase 2: Classify URLs using unified classifier"""
        print("PHASE 2: Classifying URLs (VDP, SRP, Finance)...")

        # Classify all URLs in one pass (automatically includes homepage in finance)
        result = await classify_urls(urls, domain=self.domain)

        # Map to expected format
        classified = {
            'inventory_high': result.get('vdp', []),      # VDP pages
            'inventory_medium': result.get('srp', []),    # SRP pages
            'finance': result.get('finance', []),         # Finance/tool pages (includes homepage)
            'skip': result.get('other', [])               # Everything else
        }

        # Save classified URLs to file
        os.makedirs("output", exist_ok=True)
        with open("output/classified_urls.txt", "w", encoding="utf-8") as f:
            f.write(f"# URL Classification Results (Using Specialized Classifiers)\n")
            f.write(f"# Domain: {self.domain}\n")
            f.write(f"# Total URLs: {len(urls)}\n\n")

            f.write(f"# VDP Pages (Vehicle Detail Pages) - {len(classified['inventory_high'])} URLs\n")
            f.write(f"# Single vehicle detail pages, sorted by confidence\n")
            f.write(f"# Optimized to show monthly payments\n")
            for url in classified['inventory_high']:
                f.write(f"[VDP] {url}\n")

            f.write(f"\n# SRP Pages (Search Results Pages) - {len(classified['inventory_medium'])} URLs\n")
            f.write(f"# Multiple vehicle listing pages, sorted by confidence\n")
            f.write(f"# Prioritized for pages showing monthly payments (not cash-only)\n")
            for url in classified['inventory_medium']:
                f.write(f"[SRP] {url}\n")

            f.write(f"\n# Finance/Tool Pages - {len(classified['finance'])} URLs\n")
            f.write(f"# Pages likely containing finance tools, sorted by confidence\n")
            for url in classified['finance']:
                f.write(f"[FINANCE] {url}\n")

            f.write(f"\n# Other URLs - {len(classified['skip'])} URLs\n")
            f.write(f"# Pages not relevant for tool detection or inventory\n")
            for url in classified['skip']:
                f.write(f"[OTHER] {url}\n")

        # Also save as JSON for easier parsing
        with open("output/classified_urls.json", "w", encoding="utf-8") as f:
            json.dump({
                "domain": self.domain,
                "total_urls": len(urls),
                "classification_method": "specialized_classifiers",
                "classifiers_used": ["inventory_url_classifier", "tool_url_classifier"],
                "classification": {
                    "vdp_pages": classified['inventory_high'],
                    "srp_pages": classified['inventory_medium'],
                    "finance_pages": classified['finance'],
                    "other": classified['skip']
                },
                "counts": {
                    "vdp": len(classified['inventory_high']),
                    "srp": len(classified['inventory_medium']),
                    "finance": len(classified['finance']),
                    "other": len(classified['skip'])
                }
            }, f, indent=2)

        print(f"✓ Classification complete:")
        print(f"  - VDP pages:             {len(classified['inventory_high'])}")
        print(f"  - SRP pages:             {len(classified['inventory_medium'])}")
        print(f"  - Finance/Tool pages:    {len(classified['finance'])}")
        print(f"  - Other:                 {len(classified['skip'])}")
        print(f"✓ Saved to: output/classified_urls.txt")
        print(f"✓ Saved to: output/classified_urls.json\n")

        return classified

    async def extract_inventory_phase(self, vdp_urls: list, srp_urls: list) -> list:
        """Phase 3: Extract inventory from VDP and SRP pages"""
        if not self.extract_inventory:
            print("PHASE 3: Skipped (extract_inventory=False)\n")
            return []

        print("PHASE 3: Extracting vehicle inventory...")

        # Apply separate limits to VDP and SRP
        vdp_limited = vdp_urls[:self.max_vdp_urls]
        srp_limited = srp_urls[:self.max_srp_urls]

        print(f"Processing {len(vdp_limited)} VDP pages and {len(srp_limited)} SRP pages (total: {len(vdp_limited) + len(srp_limited)})...\n")

        # Pass VDP and SRP URLs separately to extractor
        vehicles = await self.inventory_extractor.extract_with_classification(
            vdp_urls=vdp_limited,
            srp_urls=srp_limited
        )

        print(f"\n✓ Extracted {len(vehicles)} vehicles\n")
        return vehicles

    async def detect_tools_phase(self, finance_urls: list, vdp_urls: list = None, srp_urls: list = None) -> Dict[str, Any]:
        """Phase 4: Detect tools on finance, VDP, and SRP pages"""
        if not self.detect_tools:
            print("PHASE 4: Skipped (detect_tools=False)\n")
            return {tool.value: {"isPresent": False, "url": None, "notes": "Not detected"} for tool in ToolType}

        print("PHASE 4: Detecting dealership tools...")

        # ALWAYS include homepage first (highest priority)
        # Ensure domain has https:// prefix
        homepage_url = self.domain if self.domain.startswith(('http://', 'https://')) else f"https://{self.domain}"
        urls_to_process = [homepage_url]
        print(f"  Including homepage: {homepage_url}")

        # Add finance pages
        finance_sample = finance_urls[:self.max_finance_urls]
        urls_to_process.extend(finance_sample)

        # Add VDP pages for tool #8 (vdp_payments_shown)
        if vdp_urls:
            vdp_sample = vdp_urls[:min(5, len(vdp_urls))]  # Add 5 VDP pages
            urls_to_process.extend(vdp_sample)
            print(f"  Including {len(vdp_sample)} VDP pages for payment detection (tool #8)")

        # Add SRP pages for tool #7 (srp_payments_shown)
        if srp_urls:
            srp_sample = srp_urls[:min(5, len(srp_urls))]  # Add 3 SRP pages
            urls_to_process.extend(srp_sample)
            print(f"  Including {len(srp_sample)} SRP pages for payment detection (tool #7)")

        # Remove duplicates while preserving order
        seen = set()
        urls_to_process = [url for url in urls_to_process if not (url in seen or seen.add(url))]

        print(f"Processing {len(urls_to_process)} total pages (homepage + finance + inventory samples)...\n")

        # Track best findings for each tool
        tool_results = {tool.value: {"isPresent": False, "url": None, "notes": "Not found", "confidence": 0.0, "evidence": "", "location": ""} for tool in ToolType}

        if self.enable_parallel_processing and len(urls_to_process) > 1:
            # Use parallel processing
            tool_results = await self._detect_tools_parallel(urls_to_process, tool_results)
        else:
            # Use sequential processing
            tool_results = await self._detect_tools_sequential(urls_to_process, tool_results)

        detected_count = sum(1 for t in tool_results.values() if t["isPresent"])
        print(f"\n✓ Detected {detected_count}/8 tools\n")

        return tool_results

    async def _detect_tools_sequential(self, urls_to_process: list, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        """Sequential tool detection (original logic)"""
        browser_config = BrowserConfig(headless=self.headless, verbose=False)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            for i, url in enumerate(urls_to_process, 1):
                # Smart delay: Detect if page likely has popups
                delay = self.get_smart_delay(url)

                print(f"[{i}/{len(urls_to_process)}] Processing: {url[:70]}")

                # Retry logic: Try fast config first, fallback to slower config
                result = None
                for attempt in range(2):
                    try:
                        # First attempt: 30s timeout, second attempt: 90s timeout
                        timeout = 30000 if attempt == 0 else 90000

                        # Build config for tool detection (no pagination needed)
                        result = await crawler.arun(
                            url,
                            config=CrawlerRunConfig(
                                cache_mode=CacheMode.BYPASS,
                                wait_until="domcontentloaded",
                                page_timeout=timeout,
                                delay_before_return_html=delay,
                                wait_for_images=False
                            )
                        )
                        break  # Success, exit retry loop
                    except Exception as e:
                        if attempt == 0:
                            print(f"[{i}/{len(urls_to_process)}] ⚠️  Timeout (30s), retrying with 90s...")
                        else:
                            print(f"[{i}/{len(urls_to_process)}] ✗ Error: {str(e)[:80]}")
                            break

                # Skip if both attempts failed
                if result is None:
                    continue

                try:
                    if not result.success:
                        print(f"[{i}/{len(urls_to_process)}] ✗ Failed | {url[:70]}")
                        continue

                    # Get markdown text
                    markdown = str(result.markdown) if hasattr(result, 'markdown') and result.markdown else ""

                    # Check if popup detected in HTML
                    has_popup = self.detect_popup_in_html(result.html)
                    if has_popup:
                        print(f"  ⚠️  Popup detected on page, used {delay}s delay")

                    # Save markdown/HTML for debugging
                    self.save_page_debug(url, result.html, markdown, i)

                    # Detect tools on this page
                    detections = await self.tool_detector.detect(url, result.html, markdown)

                    # Update results with best findings (highest confidence)
                    found_tools = []
                    for detection in detections:
                        current = tool_results[detection.tool_name]
                        if detection.isPresent and detection.confidence > current.get("confidence", 0.0):
                            tool_results[detection.tool_name] = {
                                "isPresent": detection.isPresent,
                                "url": detection.url,
                                "notes": detection.notes,
                                "confidence": detection.confidence,
                                "evidence": detection.evidence,
                                "location": detection.location
                            }
                            found_tools.append(detection.tool_name)

                    if found_tools:
                        print(f"[{i}/{len(urls_to_process)}] ✅ Found: {', '.join(found_tools)}")
                    else:
                        print(f"[{i}/{len(urls_to_process)}] - No new tools | {url[:60]}")

                    # Early exit: Check if all 8 tools are detected
                    detected_count = sum(1 for t in tool_results.values() if t["isPresent"])
                    if detected_count == 8:
                        print(f"\n🎉 All 8 tools detected! Stopping early (processed {i}/{len(urls_to_process)} pages)")
                        break

                    await asyncio.sleep(random.uniform(1.0, 2.0))

                except Exception as e:
                    print(f"[{i}/{len(urls_to_process)}] ✗ Error: {str(e)[:50]}")

        return tool_results

    async def _detect_tools_parallel(self, urls_to_process: list, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        """Parallel tool detection for SPEED"""
        print(f"  🚀 Using parallel tool detection with {self.max_parallel_workers} workers")

        browser_config = BrowserConfig(headless=self.headless, verbose=False)

        # Step 1: Crawl all pages and collect HTML/markdown (in batches)
        pages_data = []

        async with AsyncWebCrawler(config=browser_config) as crawler:
            total_urls = len(urls_to_process)

            for batch_start in range(0, total_urls, self.max_parallel_workers):
                batch_end = min(batch_start + self.max_parallel_workers, total_urls)
                url_batch = urls_to_process[batch_start:batch_end]
                batch_num = (batch_start // self.max_parallel_workers) + 1

                print(f"  📦 Crawling batch {batch_num} ({len(url_batch)} pages)...")

                # Create crawl tasks for this batch
                async def crawl_url(url, index):
                    delay = self.get_smart_delay(url)

                    # Retry logic
                    for attempt in range(2):
                        try:
                            timeout = 30000 if attempt == 0 else 90000
                            result = await crawler.arun(
                                url,
                                config=CrawlerRunConfig(
                                    cache_mode=CacheMode.BYPASS,
                                    wait_until="domcontentloaded",
                                    page_timeout=timeout,
                                    delay_before_return_html=delay,
                                    wait_for_images=False
                                )
                            )

                            if result.success:
                                markdown = str(result.markdown) if hasattr(result, 'markdown') and result.markdown else ""
                                self.save_page_debug(url, result.html, markdown, index)
                                return {
                                    'url': url,
                                    'html': result.html,
                                    'markdown': markdown,
                                    'index': index
                                }
                            return None
                        except Exception as e:
                            if attempt == 1:
                                print(f"  ✗ Error crawling {url[:60]}: {str(e)[:50]}")
                            continue
                    return None

                # Run crawl tasks concurrently
                crawl_tasks = [crawl_url(url, batch_start + idx + 1) for idx, url in enumerate(url_batch)]
                batch_results = await asyncio.gather(*crawl_tasks, return_exceptions=True)

                for result in batch_results:
                    if result and isinstance(result, dict):
                        pages_data.append(result)

                # Small delay between batches
                if batch_end < total_urls:
                    await asyncio.sleep(1.0)

        print(f"  ✓ Crawled {len(pages_data)} pages successfully")

        # Step 2: Detect tools on all pages in parallel
        if pages_data:
            all_detections = await self.tool_detector.detect_batch_parallel(pages_data)

            # Step 3: Update results with best findings
            for page_detections in all_detections:
                found_tools = []
                for detection in page_detections:
                    current = tool_results[detection.tool_name]
                    if detection.isPresent and detection.confidence > current.get("confidence", 0.0):
                        tool_results[detection.tool_name] = {
                            "isPresent": detection.isPresent,
                            "url": detection.url,
                            "notes": detection.notes,
                            "confidence": detection.confidence,
                            "evidence": detection.evidence,
                            "location": detection.location
                        }
                        found_tools.append(detection.tool_name)

                if found_tools:
                    print(f"  ✅ Found: {', '.join(found_tools)}")

        return tool_results

    def save_results(self, vehicles: list, tools: Dict[str, Any]):
        """Save results to JSON files"""
        print("="*80)
        print("SAVING RESULTS")
        print("="*80)

        os.makedirs("output", exist_ok=True)

        # Save inventory JSON (always save, even if empty)
        if self.extract_inventory:
            with open("output/inventory.json", "w", encoding="utf-8") as f:
                json.dump(vehicles if vehicles else [], f, indent=2, ensure_ascii=False)
            vehicle_count = len(vehicles) if vehicles else 0
            print(f"✓ Saved: output/inventory.json ({vehicle_count} vehicles)")

        # Save tools JSON
        if self.detect_tools:
            # Format tools for output
            tools_output = [
                {
                    "tool_name": name,
                    "is_present": data["isPresent"],  # Changed to snake_case for consistency
                    "confidence": data.get("confidence", 0.0),
                    "url": data.get("url") or "",
                    "evidence": data.get("evidence", ""),
                    "location": data.get("location", ""),
                    "notes": data.get("notes", "")
                }
                for name, data in tools.items()
            ]

            with open("output/tools.json", "w", encoding="utf-8") as f:
                json.dump(tools_output, f, indent=2, ensure_ascii=False)

            detected = sum(1 for t in tools.values() if t["isPresent"])
            print(f"✓ Saved: output/tools.json ({detected}/8 tools detected)")

        print("\n" + "="*80)
        print("COMPLETE!")
        print("="*80)

    def get_smart_delay(self, url: str) -> float:
        """
        Determine delay after networkidle

        Since we use wait_until="networkidle", the crawler already waits for
        network activity to settle. This additional delay gives time for any
        post-load animations or delayed popups.

        Returns:
            Delay in seconds (shorter since networkidle handles most waiting)
        """
        import re

        # URLs that commonly have delayed popups (after network is idle)
        delayed_popup_patterns = [
            r'/pre[-_]?qual',           # Pre-qualification pages
            r'/get[-_]?financing',      # Financing pages
            r'/apply',                  # Application pages
            r'/credit[-_]?app',         # Credit application
            r'/finance',                # Finance pages
            r'/trade[-_]?in',           # Trade-in pages
            r'/value[-_]?trade',        # Trade value pages
            r'/specials',               # Special offers (often have popups)
            r'/calculator',             # Calculator pages
        ]

        url_lower = url.lower()
        for pattern in delayed_popup_patterns:
            if re.search(pattern, url_lower):
                return 3.0  # Extra 3s for delayed popups (networkidle already waited)

        return 1.0  # Just 1s for normal pages (networkidle already waited)

    def detect_popup_in_html(self, html: str) -> bool:
        """
        Detect if HTML contains popup/modal indicators

        Returns:
            True if popup detected
        """
        import re

        popup_indicators = [
            r'class=["\'][^"\']*modal[^"\']*["\']',
            r'class=["\'][^"\']*popup[^"\']*["\']',
            r'class=["\'][^"\']*overlay[^"\']*["\']',
            r'class=["\'][^"\']*dialog[^"\']*["\']',
            r'role=["\']dialog["\']',
            r'aria-modal=["\']true["\']',
        ]

        for pattern in popup_indicators:
            if re.search(pattern, html, re.IGNORECASE):
                return True

        return False

    def save_page_debug(self, url: str, html: str, markdown: str, index: int):
        """Save page HTML and markdown for debugging"""
        import re
        # Create safe filename from URL
        safe_url = re.sub(r'[^\w\-]', '_', url.replace('https://', '').replace('http://', ''))
        safe_url = safe_url[:100]  # Limit length

        debug_dir = "output/debug"
        os.makedirs(debug_dir, exist_ok=True)

        # Save HTML
        html_file = f"{debug_dir}/{index:03d}_{safe_url}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(f"<!-- URL: {url} -->\n")
            f.write(html)

        # Save markdown
        md_file = f"{debug_dir}/{index:03d}_{safe_url}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# URL: {url}\n\n")
            f.write(markdown)

        # Save iframe analysis
        import re
        iframes = re.findall(r'<iframe[^>]*src=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE)
        if iframes:
            iframe_file = f"{debug_dir}/{index:03d}_{safe_url}_iframes.txt"
            with open(iframe_file, "w", encoding="utf-8") as f:
                f.write(f"URL: {url}\n")
                f.write(f"Found {len(iframes)} iframe(s):\n\n")
                for iframe_url in iframes:
                    f.write(f"  - {iframe_url}\n")

    def load_classified_urls_from_file(self) -> Dict[str, list]:
        """Load previously classified URLs from JSON file"""
        print("Loading classified URLs from file...")

        json_path = "output/classified_urls.json"
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"❌ File not found: {json_path}\nRun with skip_classification=False first to generate it.")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        classified = {
            'inventory_high': data['classification']['vdp_pages'],
            'inventory_medium': data['classification']['srp_pages'],
            'finance': data['classification']['finance_pages'],
            'skip': data['classification'].get('other', data['classification'].get('skipped', []))
        }

        print(f"✓ Loaded from: {json_path}")
        print(f"  - VDP pages:             {len(classified['inventory_high'])}")
        print(f"  - SRP pages:             {len(classified['inventory_medium'])}")
        print(f"  - Finance/Tool pages:    {len(classified['finance'])}")
        print(f"  - Other:                 {len(classified['skip'])}\n")

        return classified

    async def run(self, skip_classification: bool = False):
        """
        Main execution flow

        Args:
            skip_classification: If True, skip phases 1 & 2 and load URLs from output/classified_urls.json
        """
        logger.info("="*80)
        logger.info("SCRAPER: Starting run method")
        logger.info("="*80)

        self.print_config()

        if skip_classification:
            logger.info("FAST MODE: Skipping URL seeding and classification")
            logger.info("="*80)

            # Load classified URLs from file
            logger.info("SCRAPER: Loading classified URLs from file")
            classified = self.load_classified_urls_from_file()
        else:
            # Phase 1: Seed URLs
            logger.info("SCRAPER: Phase 1 - Seeding URLs")
            all_urls = await self.seed_urls()

            # Phase 2: Classify URLs
            logger.info("SCRAPER: Phase 2 - Classifying URLs")
            classified = await self.classify_urls_phase(all_urls)

        # Phase 3: Extract Inventory (pass VDP and SRP separately)
        logger.info("SCRAPER: Phase 3 - Extracting inventory")
        vehicles = await self.extract_inventory_phase(
            vdp_urls=classified['inventory_high'],
            srp_urls=classified['inventory_medium']
        )

        # Phase 4: Detect Tools (pass finance + VDP + SRP URLs)
        logger.info("SCRAPER: Phase 4 - Detecting tools")
        tools = await self.detect_tools_phase(
            finance_urls=classified['finance'],
            vdp_urls=classified['inventory_high'],  # VDP for tool #8
            srp_urls=classified['inventory_medium']  # SRP for tool #7
        )

        # Save Results
        logger.info("SCRAPER: Saving results")
        self.save_results(vehicles, tools)

        logger.info("SCRAPER: Run method completed successfully")
        logger.info("="*80)


async def main():
    """Entry point - All configuration from environment variables"""

    logger.info("="*80)
    logger.info("SCRAPER STARTING")
    logger.info("="*80)

    # Required environment variables
    DOMAIN = os.getenv("SCRAPER_DOMAIN")
    # DOMAIN = "https://www.cardinalenissan.com"
    API_KEY = os.getenv("OPENAI_API_KEY")

    logger.info(f"Domain: {DOMAIN}")
    logger.info(f"API Key: {'SET' if API_KEY else 'NOT SET'}")

    if not API_KEY:
        logger.error("OPENAI_API_KEY environment variable not set")
        raise ValueError("OPENAI_API_KEY environment variable is required")

    if not DOMAIN:
        logger.error("SCRAPER_DOMAIN environment variable not set")
        raise ValueError("SCRAPER_DOMAIN environment variable is required")

    # Optional configuration from environment variables (with defaults)
    extract_inventory = os.getenv("SCRAPER_EXTRACT_INVENTORY", "true").lower() == "true"
    detect_tools = os.getenv("SCRAPER_DETECT_TOOLS", "true").lower() == "true"
    max_vdp_urls = int(os.getenv("SCRAPER_MAX_VDP_URLS", "100"))
    max_srp_urls = int(os.getenv("SCRAPER_MAX_SRP_URLS", "50"))
    max_finance_urls = int(os.getenv("SCRAPER_MAX_FINANCE_URLS", "200"))
    enable_pagination = os.getenv("SCRAPER_ENABLE_PAGINATION", "true").lower() == "true"
    max_pages_per_url = int(os.getenv("SCRAPER_MAX_PAGES_PER_URL", "40"))
    headless = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"
    enable_parallel = os.getenv("SCRAPER_ENABLE_PARALLEL", "true").lower() == "true"
    max_workers = int(os.getenv("SCRAPER_MAX_WORKERS", "3"))
    detection_strictness = os.getenv("SCRAPER_DETECTION_STRICTNESS", "lenient")
    skip_classification = os.getenv("SCRAPER_SKIP_CLASSIFICATION", "false").lower() == "true"

    # Proxy configuration
    use_proxy = os.getenv("SCRAPER_USE_PROXY", "false").lower() == "true"
    proxy_config = None
    if use_proxy:
        proxy_config = {
            'server': os.getenv('SCRAPER_PROXY_SERVER'),
            'username': os.getenv('SCRAPER_PROXY_USERNAME'),
            'password': os.getenv('SCRAPER_PROXY_PASSWORD')
        }
        logger.info(f"Proxy: ENABLED ({proxy_config['server']})")
    else:
        logger.info("Proxy: DISABLED")

    logger.info("Config:")
    logger.info(f"  Extract Inventory: {extract_inventory}")
    logger.info(f"  Detect Tools: {detect_tools}")
    logger.info(f"  Max VDP URLs: {max_vdp_urls}")
    logger.info(f"  Max SRP URLs: {max_srp_urls}")
    logger.info(f"  Headless: {headless}")
    logger.info("="*80)

    # Initialize scraper
    logger.info("Initializing scraper...")
    scraper = DealershipScraper(
        domain=DOMAIN,
        api_key=API_KEY,
        extract_inventory=extract_inventory,
        detect_tools=detect_tools,
        max_vdp_urls=max_vdp_urls,
        max_srp_urls=max_srp_urls,
        max_finance_urls=max_finance_urls,
        enable_inventory_pagination=enable_pagination,
        max_pages_per_url=max_pages_per_url,
        headless=headless,
        enable_parallel_processing=enable_parallel,
        max_parallel_workers=max_workers,
        detection_strictness=detection_strictness,
        proxy_config=proxy_config
    )
    logger.info("Scraper initialized successfully")

    # Run scraper
    logger.info("Starting scraper run...")
    await scraper.run(skip_classification=skip_classification)
    logger.info("Scraper completed successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error("="*80)
        logger.error("FATAL ERROR IN SCRAPER")
        logger.error("="*80)
        logger.error(f"Error: {str(e)}")
        logger.error("Full traceback:")
        import traceback
        traceback.print_exc()
        raise


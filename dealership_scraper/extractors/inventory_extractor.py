"""
Inventory Extraction Module
Extracts vehicle data from dealership pages using LLM
Uses the EXACT same approach as url_seeding_crawler.py

Optimizations:
1. Enhanced content filtering: Removes navbars, chat widgets, legal disclaimers
2. Data normalization: Ensures all enum fields match models.py values
3. VIN enrichment: Fills missing fields using NHTSA VIN decoder API
4. Pagination support: Handles traditional pagination, load more buttons, and infinite scroll
"""
from typing import List, Dict, Any, Optional
import asyncio
import random
import logging
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMConfig, BrowserConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from ..models import Vehicle
from ..enrichment import VINEnricher, DataNormalizer
from .pagination_handler import PaginationDetector, PaginationHandler, PaginationType

# Get logger
logger = logging.getLogger(__name__)


class CarInventoryPage(BaseModel):
    """Schema for a page containing car inventory - EXACT copy from url_seeding_crawler.py"""
    cars: List[Vehicle] = Field(description="List of all cars found on this page")
    page_type: str = Field(description="Type of page: new inventory, used inventory, category, etc.")


class EnhancedContentFilter(PruningContentFilter):
    """
    Enhanced content filter that removes navigation, chat widgets, legal disclaimers
    NO CSS selectors - just broad content type filtering
    """
    def __init__(self):
        super().__init__()
        # Add more unwanted patterns (NO CSS selectors, just common patterns)
        self.excluded_tags.update({
            'aside',      # Sidebars
            'form',       # Forms (unless needed for inventory)
        })
        # Enhanced negative patterns for class/id matching
        self.negative_patterns = __import__('re').compile(
            r'nav|footer|header|sidebar|widget|chat|legal|disclaimer|'
            r'cookie|consent|privacy|terms|policy|ads|advert|promo|'
            r'social|share|comment|breadcrumb|pagination',
            __import__('re').I
        )


class InventoryExtractor:
    """Extracts vehicle inventory from dealership pages with VIN enrichment and pagination support"""

    def __init__(
        self,
        api_key: str,
        enrich_with_vin: bool = True,
        enable_pagination: bool = False,
        max_pages_per_url: int = 40,
        headless: bool = True,
        enable_parallel: bool = False,
        max_workers: int = 3,
        proxy_config: Optional[Dict[str, str]] = None
    ):
        """
        Args:
            api_key: OpenRouter API key
            enrich_with_vin: Enable VIN enrichment using NHTSA API (default: True)
                            Fills missing fields like trim, transmission, fuel_type, safety features
            enable_pagination: Enable automatic pagination detection and navigation (default: True)
            max_pages_per_url: Maximum pages to crawl per URL (default: 10)
            headless: Run browser in headless mode (default: True)
            enable_parallel: Enable parallel processing of URLs (default: False)
            max_workers: Maximum parallel workers (default: 3)
            proxy_config: Optional proxy configuration dict with keys:
                         - server: Proxy server URL (e.g., "http://gate.dc.smartproxy.com:20000")
                         - username: Proxy username
                         - password: Proxy password
        """
        self.api_key = api_key
        self.headless = headless
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self.proxy_config = proxy_config
        self.vin_enricher = VINEnricher() if enrich_with_vin else None
        self.enable_pagination = enable_pagination
        self.pagination_handler = PaginationHandler(
            max_pages=max_pages_per_url,
            scroll_pause_time=2.0,
            max_scroll_attempts=5
        )
        self.llm_config = LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=api_key,
            base_url="https://openrouter.ai/api/v1"
        )

    async def extract(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extract vehicles from URLs (legacy method - treats all as single page)

        Args:
            urls: List of inventory page URLs

        Returns:
            List of vehicle dictionaries
        """
        all_vehicles = await self._extract_single_page(urls)

        # Log VIN enrichment stats
        if self.vin_enricher and self.vin_enricher.stats['enriched_vehicles'] > 0:
            self.vin_enricher.print_stats()

        return all_vehicles

    async def extract_with_classification(self, vdp_urls: List[str], srp_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extract vehicles from pre-classified VDP and SRP URLs

        Args:
            vdp_urls: List of VDP (Vehicle Detail Page) URLs
            srp_urls: List of SRP (Search Results Page) URLs

        Returns:
            List of vehicle dictionaries
        """
        all_vehicles = []

        # VDP pages: ALWAYS no pagination (single page extraction)
        if vdp_urls:
            logger.info(f"  Extracting {len(vdp_urls)} VDP pages (no pagination)...")
            vdp_vehicles = await self._extract_single_page(vdp_urls)
            all_vehicles.extend(vdp_vehicles)

        # SRP pages: pagination controlled by enable_pagination flag
        if srp_urls:
            if self.enable_pagination:
                logger.info(f"  Extracting {len(srp_urls)} SRP pages (with pagination, max {self.pagination_handler.max_pages} pages/URL)...")
                srp_vehicles = await self._extract_with_pagination(srp_urls)
            else:
                logger.info(f"  Extracting {len(srp_urls)} SRP pages (no pagination)...")
                srp_vehicles = await self._extract_single_page(srp_urls)
            all_vehicles.extend(srp_vehicles)

        # Log VIN enrichment stats
        if self.vin_enricher and self.vin_enricher.stats['enriched_vehicles'] > 0:
            self.vin_enricher.print_stats()

        return all_vehicles

    async def _extract_with_pagination(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Extract vehicles with pagination support"""
        all_vehicles = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)

            for i, url in enumerate(urls, 1):
                # Add delay between requests to avoid rate limiting (except first URL)
                if i > 1:
                    delay = random.uniform(2.0, 4.0)
                    await asyncio.sleep(delay)

                # Retry logic: Try twice if 0 vehicles found
                for attempt in range(2):
                    try:
                        logger.info(f"\n[{i}/{len(urls)}] Processing: {url[:70]}")

                        # Create a new page
                        page = await browser.new_page()

                        # Enable request interception to log navigation
                        current_page_url = [url]  # Store current URL for printing

                        async def log_navigation(route):
                            # Just pass through, we only want to observe
                            await route.continue_()

                        await page.route('**/*', log_navigation)
                        await page.goto(url, wait_until='domcontentloaded', timeout=60000)

                        # Wait for content to load
                        await page.wait_for_timeout(3000)

                        # Get initial HTML
                        html = await page.content()

                        # Detect pagination type
                        pagination_type, metadata = await PaginationDetector.detect(page, html)

                        # Navigate through all pages and collect HTML
                        all_html_pages = await self.pagination_handler.paginate(page, pagination_type, metadata)

                        logger.info(f"  ✓ Collected {len(all_html_pages)} page(s) of content")

                        # Extract vehicles from all collected HTML
                        url_vehicles = []
                        for page_num, html_content in enumerate(all_html_pages, 1):
                            # Log page number (not using page.url since browser may have navigated further)
                            logger.info(f"  📄 Extracting from page {page_num} of {len(all_html_pages)}")

                            vehicles = await self._extract_from_html(html_content, url)

                            if vehicles:
                                # Mark page number for tracking
                                for vehicle in vehicles:
                                    vehicle['page_number'] = page_num

                                url_vehicles.extend(vehicles)

                        # Retry if 0 vehicles found on first attempt
                        if len(url_vehicles) == 0 and attempt == 0:
                            logger.warning(f"[{i}/{len(urls)}] ⚠️  0 vehicles found, retrying...")
                            await page.close()
                            continue

                        # Deduplicate vehicles (by VIN or stock number)
                        url_vehicles = self._deduplicate_vehicles(url_vehicles)

                        logger.info(f"  ✓ Total unique vehicles from this URL: {len(url_vehicles)}")
                        all_vehicles.extend(url_vehicles)

                        await page.close()
                        break  # Success, exit retry loop

                    except Exception as e:
                        if attempt == 0:
                            logger.warning(f"[{i}/{len(urls)}] ⚠️  Error, retrying: {str(e)[:100]}")
                            try:
                                await page.close()
                            except:
                                pass
                        else:
                            logger.error(f"[{i}/{len(urls)}] ✗ Error after retry: {str(e)[:100]}")

                        if attempt == 1:  # Last attempt
                            break

            await browser.close()

        return all_vehicles

    async def _extract_single_page(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Original single-page extraction (no pagination)"""
        if self.enable_parallel and len(urls) > 1:
            # Use parallel processing
            return await self._extract_single_page_parallel(urls)
        else:
            # Use sequential processing
            return await self._extract_single_page_sequential(urls)

    async def _extract_single_page_sequential(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Sequential single-page extraction"""
        all_vehicles = []

        # EXACT extraction instruction from url_seeding_crawler.py
        extraction_strategy = LLMExtractionStrategy(
            llm_config=self.llm_config,
            schema=CarInventoryPage.model_json_schema(),
            extraction_type="schema",
            instruction=self._get_extraction_instruction(),
            verbose=False,
            chunk_token_threshold=8000  # Increased from 4000 to handle larger pages without chunking
        )

        # EXACT crawler config from url_seeding_crawler.py
        crawler_config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=EnhancedContentFilter()
            ),
            extraction_strategy=extraction_strategy,
            page_timeout=90000,
            delay_before_return_html=5,
            excluded_tags=['header', 'footer', 'nav', 'aside'],
            verbose=False
        )

        browser_cfg = BrowserConfig(
            browser_type="chromium",
            headless=self.headless,
            verbose=True,
            proxy_config=self.proxy_config if self.proxy_config else None
        )
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            for i, url in enumerate(urls, 1):
                # Add delay between requests to avoid rate limiting (except first URL)
                if i > 1:
                    delay = random.uniform(2.0, 4.0)
                    await asyncio.sleep(delay)

                # Retry logic: Try twice if 0 vehicles found
                for attempt in range(2):
                    try:
                        result = await crawler.arun(url, config=crawler_config)

                        if result.success and result.extracted_content:
                            import json
                            data = json.loads(result.extracted_content)

                            # EXACT parsing logic from url_seeding_crawler.py
                            page_cars = []
                            page_type = 'unknown'

                            if isinstance(data, list):
                                for block in data:
                                    if isinstance(block, dict) and 'cars' in block:
                                        page_cars.extend(block.get('cars', []))
                                        if not page_type or page_type == 'unknown':
                                            page_type = block.get('page_type', 'unknown')
                            elif isinstance(data, dict) and 'cars' in data:
                                page_cars = data.get('cars', [])
                                page_type = data.get('page_type', 'unknown')

                            # Retry if 0 vehicles found on first attempt
                            if len(page_cars) == 0 and attempt == 0:
                                logger.warning(f"[{i}/{len(urls)}] ⚠️  0 vehicles found, retrying...")
                                continue

                            # Add source URL and page_type to each vehicle
                            for vehicle in page_cars:
                                if isinstance(vehicle, dict):
                                    vehicle['source_url'] = url
                                    vehicle['page_type'] = page_type

                                    # Normalize scraped data to match enum values
                                    vehicle = DataNormalizer.normalize_vehicle(vehicle)

                                    # VIN enrichment (if enabled) - fills missing fields
                                    if self.vin_enricher and vehicle.get('vin'):
                                        vehicle = self.vin_enricher.enrich_vehicle(vehicle)

                                    # Normalize again after VIN enrichment to ensure consistency
                                    vehicle = DataNormalizer.normalize_vehicle(vehicle)

                                    all_vehicles.append(vehicle)

                            logger.info(f"[{i}/{len(urls)}] ✓ {len(page_cars)} vehicles | {url[:70]}")
                            break  # Success, exit retry loop
                        else:
                            if attempt == 0:
                                logger.warning(f"[{i}/{len(urls)}] ⚠️  No data, retrying...")
                            else:
                                logger.info(f"[{i}/{len(urls)}] - No data after retry | {url[:70]}")

                            if attempt == 1:  # Last attempt
                                break

                    except Exception as e:
                        if attempt == 0:
                            logger.warning(f"[{i}/{len(urls)}] ⚠️  Error, retrying: {str(e)[:50]}")
                        else:
                            logger.error(f"[{i}/{len(urls)}] ✗ Error after retry: {str(e)[:50]} | {url[:50]}")

                        if attempt == 1:  # Last attempt
                            break

        return all_vehicles

    async def _extract_single_page_parallel(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Parallel single-page extraction for SPEED"""
        logger.info(f"  🚀 Using parallel processing with {self.max_workers} workers")

        all_vehicles = []

        # Process URLs in batches
        async def process_url_batch(url_batch, batch_num):
            """Process a batch of URLs concurrently"""
            batch_vehicles = []

            # Create extraction strategy
            extraction_strategy = LLMExtractionStrategy(
                llm_config=self.llm_config,
                schema=CarInventoryPage.model_json_schema(),
                extraction_type="schema",
                instruction=self._get_extraction_instruction(),
                verbose=False,
                chunk_token_threshold=8000
            )

            crawler_config = CrawlerRunConfig(
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=EnhancedContentFilter()
                ),
                extraction_strategy=extraction_strategy,
                page_timeout=90000,
                delay_before_return_html=5,
                excluded_tags=['header', 'footer', 'nav', 'aside'],
                verbose=False
            )

            browser_cfg = BrowserConfig(
                browser_type="chromium",
                headless=self.headless,
                verbose=False,  # Reduce noise in parallel mode
                proxy_config=self.proxy_config if self.proxy_config else None
            )

            # Process each URL in the batch
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                tasks = []
                for url in url_batch:
                    tasks.append(self._extract_url(crawler, url, crawler_config))

                # Run all tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for vehicles in results:
                    if isinstance(vehicles, list):
                        batch_vehicles.extend(vehicles)

            return batch_vehicles

        # Split URLs into batches
        total_urls = len(urls)
        for batch_start in range(0, total_urls, self.max_workers):
            batch_end = min(batch_start + self.max_workers, total_urls)
            url_batch = urls[batch_start:batch_end]
            batch_num = (batch_start // self.max_workers) + 1

            logger.info(f"  📦 Processing batch {batch_num} ({len(url_batch)} URLs)...")

            batch_vehicles = await process_url_batch(url_batch, batch_num)
            all_vehicles.extend(batch_vehicles)

            # Small delay between batches
            if batch_end < total_urls:
                await asyncio.sleep(1.0)

        return all_vehicles

    async def _extract_url(self, crawler, url: str, crawler_config) -> List[Dict[str, Any]]:
        """Extract vehicles from a single URL (for parallel processing)"""
        vehicles = []

        try:
            result = await crawler.arun(url, config=crawler_config)

            if result.success and result.extracted_content:
                import json
                data = json.loads(result.extracted_content)

                page_cars = []
                page_type = 'unknown'

                if isinstance(data, list):
                    for block in data:
                        if isinstance(block, dict) and 'cars' in block:
                            page_cars.extend(block.get('cars', []))
                            if not page_type or page_type == 'unknown':
                                page_type = block.get('page_type', 'unknown')
                elif isinstance(data, dict) and 'cars' in data:
                    page_cars = data.get('cars', [])
                    page_type = data.get('page_type', 'unknown')

                # Process vehicles
                for vehicle in page_cars:
                    if isinstance(vehicle, dict):
                        vehicle['source_url'] = url
                        vehicle['page_type'] = page_type

                        vehicle = DataNormalizer.normalize_vehicle(vehicle)

                        if self.vin_enricher and vehicle.get('vin'):
                            vehicle = self.vin_enricher.enrich_vehicle(vehicle)

                        vehicle = DataNormalizer.normalize_vehicle(vehicle)
                        vehicles.append(vehicle)

                logger.info(f"  ✓ {len(page_cars)} vehicles | {url[:60]}")
            else:
                logger.info(f"  - No data | {url[:60]}")

        except Exception as e:
            logger.error(f"  ✗ Error: {str(e)[:50]} | {url[:50]}")

        return vehicles

    async def _extract_from_html(self, html: str, source_url: str) -> List[Dict[str, Any]]:
        """Extract vehicles from HTML content using schema-based extraction via AsyncWebCrawler"""
        vehicles = []

        try:
            import json
            import tempfile
            import os

            # Save HTML to temp file so we can crawl it with AsyncWebCrawler
            # This ensures we use the same extraction pipeline as _extract_single_page
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html)
                temp_file = f.name

            try:
                # Use the same extraction strategy as _extract_single_page
                extraction_strategy = LLMExtractionStrategy(
                    llm_config=self.llm_config,
                    schema=CarInventoryPage.model_json_schema(),
                    extraction_type="schema",
                    instruction=self._get_extraction_instruction(),
                    verbose=False,
                    chunk_token_threshold=8000  # Increased from 4000 to handle larger pages without chunking
                )

                crawler_config = CrawlerRunConfig(
                    markdown_generator=DefaultMarkdownGenerator(
                        content_filter=EnhancedContentFilter()
                    ),
                    extraction_strategy=extraction_strategy,
                    page_timeout=30000,
                    excluded_tags=['header', 'footer', 'nav', 'aside'],
                    verbose=False
                )
                browser_cfg = BrowserConfig(
                    browser_type="chromium",
                    headless=self.headless,
                    verbose=True,
                    proxy_config=self.proxy_config if self.proxy_config else None
                )
                # Crawl the temp file
                async with AsyncWebCrawler(config=browser_cfg) as crawler:
                    result = await crawler.arun(f"file://{temp_file}", config=crawler_config)

                    if result.success and result.extracted_content:
                        data = json.loads(result.extracted_content)
                    else:
                        return vehicles

            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

            if not data:
                return vehicles

            # EXACT parsing logic from _extract_single_page
            page_cars = []
            page_type = 'unknown'

            if isinstance(data, list):
                for block in data:
                    if isinstance(block, dict) and 'cars' in block:
                        page_cars.extend(block.get('cars', []))
                        if not page_type or page_type == 'unknown':
                            page_type = block.get('page_type', 'unknown')
            elif isinstance(data, dict) and 'cars' in data:
                page_cars = data.get('cars', [])
                page_type = data.get('page_type', 'unknown')

            logger.info(f"    📦 Extracted {len(page_cars)} vehicles from HTML")

            # Process vehicles
            for vehicle in page_cars:
                if isinstance(vehicle, dict):
                    vehicle['source_url'] = source_url
                    vehicle['page_type'] = page_type

                    # Normalize scraped data
                    vehicle = DataNormalizer.normalize_vehicle(vehicle)

                    # VIN enrichment (if enabled)
                    if self.vin_enricher and vehicle.get('vin'):
                        vehicle = self.vin_enricher.enrich_vehicle(vehicle)

                    # Normalize again after enrichment
                    vehicle = DataNormalizer.normalize_vehicle(vehicle)

                    vehicles.append(vehicle)

        except Exception as e:
            logger.error(f"    ⚠️  Error extracting from HTML: {str(e)[:200]}")
            import traceback
            logger.error(f"    Traceback: {traceback.format_exc()[:300]}")

        return vehicles

    def _deduplicate_vehicles(self, vehicles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate vehicles based on VIN or stock number"""
        seen = set()
        unique_vehicles = []

        for vehicle in vehicles:
            # Create unique key
            vin = vehicle.get('vin')
            stock = vehicle.get('stock_number')

            key = None
            if vin:
                key = f"vin:{vin}"
            elif stock:
                key = f"stock:{stock}"
            else:
                # Use combination of year, make, model, mileage
                key = f"{vehicle.get('year')}:{vehicle.get('make')}:{vehicle.get('model')}:{vehicle.get('mileage')}"

            if key not in seen:
                seen.add(key)
                unique_vehicles.append(vehicle)

        if len(vehicles) != len(unique_vehicles):
            logger.info(f"    ℹ️  Removed {len(vehicles) - len(unique_vehicles)} duplicate vehicles")

        return unique_vehicles

    def _get_extraction_instruction(self) -> str:
        """Get LLM extraction instruction"""
        return """Extract ALL car inventory data from this ENTIRE page. This is CRITICAL - you must find EVERY SINGLE vehicle.

CRITICAL EXTRACTION RULES:
1. **SCAN THE ENTIRE PAGE** - Do NOT skip any vehicles, even if there are many
2. If this is a listing page with 30+ vehicles, extract ALL 30+ vehicles - no exceptions
3. Each car = ONE entry in the 'cars' array (do NOT split a single car across multiple entries)
4. Do NOT create duplicate entries for the same vehicle
5. Each car MUST have at minimum: year, make, and model filled in
6. If a field is missing, use null (NOT empty string, "Not specified", "N/A", "None")
7. VIN must be exactly 17 alphanumeric characters - if invalid, use null

PRICING RULES (CRITICAL):
- "price": Extract the SELLING PRICE (dealer price, our price, sale price) as a number (e.g., 25995.00)
- If both MSRP and selling price exist, use the SELLING PRICE (lower price), NOT MSRP
- Do NOT extract monthly payments as the price
- If you see "$366/month" or "Lease: $366/mo", put that in "monthly_payment" field, NOT in "price"
- If only monthly payment is shown with no full price, leave "price" as null
- "currency": Extract currency symbol or code (e.g., "USD", "$", "CAD")
- Remove any commas, dollar signs, or text from price - numbers only

EXTRACTION STRATEGY FOR LISTING PAGES:
- Look for repeating patterns (vehicle cards, table rows, list items)
- Each repeating element likely represents ONE vehicle
- Extract data from ALL repeating elements - do not stop early
- If you see 40 vehicle cards on the page, you should extract 40 vehicles
- Count the vehicles as you go to ensure you don't miss any

EXTRACTION STRATEGY FOR DETAIL PAGES:
- Extract the ONE vehicle shown on the page
- Get ALL available details for that vehicle

Example output for LISTING PAGE (30 vehicles):
{
"cars": [
  {"year": "2024", "make": "Toyota", "model": "Camry", "trim": "LE", "price": 28500.00, "vin": "1234567890ABCDEFG", ...},
  {"year": "2023", "make": "Honda", "model": "Accord", "trim": "EX", "price": 26999.00, "vin": "2345678901BCDEFGH", ...},
  ... (repeat for ALL vehicles on page - if there are 30 vehicles, include all 30!)
],
"page_type": "multiple vehicle listing page"
}

Example output for DETAIL PAGE (1 vehicle):
{
"cars": [
{
    "year": "2025",
    "make": "Nissan",
    "model": "Kicks",
    "trim": "SV",
    "price": 25995.00,
    "currency": "USD",
    "monthly_payment": null,
    "condition": "New",
    "vin": "3N8AP6DA4SL372859",
    "vehicle_type": "SUV",
    "stock_number": "ABC123",
    "mileage": "0",
    "drivetrain": "FWD",
    "transmission": "CVT",
    "fuel_type": "Gasoline",
    "doors": 4,
    "engine": "2.0L 4-Cylinder",
    "exterior_color": "Scarlet Ember",
    "interior_color": "Charcoal",
    "seating_capacity": 5,
    "features": ["Bluetooth", "Backup Camera", "Apple CarPlay"],
    "safety_features": ["Automatic Emergency Braking", "Lane Departure Warning"],
    "warranty": "3 year/36,000 mile",
    "special_offers": "$500 dealer discount"
}
],
"page_type": "single vehicle detail page"
}

REMEMBER: Extract EVERY vehicle - missing even one vehicle is a failure!"""

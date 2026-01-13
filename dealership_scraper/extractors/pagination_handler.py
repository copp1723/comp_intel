"""
Universal Pagination Handler Module
Detects and handles different types of pagination across ANY dealership website:
1. Traditional pagination (numbered links, next/prev buttons)
2. "Load More" buttons
3. Infinite scroll / lazy loading
4. URL-based pagination (query params)
5. JavaScript-rendered pagination
"""
import asyncio
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

# Get logger
logger = logging.getLogger(__name__)


class PaginationType(Enum):
    """Types of pagination"""
    NONE = "none"
    TRADITIONAL = "traditional"  # Page numbers, next/prev buttons
    LOAD_MORE = "load_more"      # "Load More" or "Show More" button
    INFINITE_SCROLL = "infinite_scroll"  # Lazy loading on scroll
    URL_BASED = "url_based"      # ?page=2, /page/2, etc.


class PaginationDetector:
    """Universal pagination detector that works across all dealership websites"""

    @staticmethod
    async def detect(page: Page, html: str) -> Tuple[PaginationType, Dict[str, Any]]:
        """
        Universally detect pagination type on ANY page

        Args:
            page: Playwright page object
            html: Page HTML content

        Returns:
            Tuple of (PaginationType, metadata dict)
        """
        metadata = {}

        logger.info("  🔍 Detecting pagination...")

        # STRATEGY 1: Look for "Load More" buttons (most common on modern sites)
        load_more_result = await PaginationDetector._detect_load_more(page)
        if load_more_result:
            logger.info(f"  ✓ Detected: Load More button")
            return (PaginationType.LOAD_MORE, load_more_result)

        # STRATEGY 2: Look for traditional pagination (next buttons, page numbers)
        traditional_result = await PaginationDetector._detect_traditional(page)
        if traditional_result:
            logger.info(f"  ✓ Detected: Traditional pagination")
            return (PaginationType.TRADITIONAL, traditional_result)

        # STRATEGY 3: Check for infinite scroll
        scroll_result = await PaginationDetector._detect_infinite_scroll(page, html)
        if scroll_result:
            logger.info(f"  ✓ Detected: Infinite scroll")
            return (PaginationType.INFINITE_SCROLL, scroll_result)

        # No pagination detected
        logger.info("  ℹ️  No pagination detected")
        return (PaginationType.NONE, metadata)

    @staticmethod
    async def _detect_load_more(page: Page) -> Optional[Dict[str, Any]]:
        """Detect 'Load More' style buttons - UNIVERSAL approach"""

        # Comprehensive patterns for load more text
        load_more_patterns = [
            'load', 'more', 'show', 'view', 'see',
            'additional', 'results', 'vehicles', 'inventory',
            'expand', 'display', 'reveal'
        ]

        # Get ALL clickable elements
        clickable_elements = await page.query_selector_all('button, a, div[onclick], span[onclick], [role="button"]')

        for element in clickable_elements:
            try:
                # Check if visible
                is_visible = await element.is_visible()
                if not is_visible:
                    continue

                # Get text content
                text = await element.text_content()
                if not text:
                    continue

                text_lower = text.lower().strip()

                # Check if text matches load more patterns
                # Looking for combinations like "load more", "show more results", etc.
                matches = sum(1 for pattern in load_more_patterns if pattern in text_lower)

                if matches >= 2 or any(phrase in text_lower for phrase in [
                    'load more', 'show more', 'view more', 'see more',
                    'more results', 'more vehicles', 'load all'
                ]):
                    # Found a load more button!
                    return {
                        'button_element': element,
                        'button_text': text.strip(),
                        'selector': 'dynamic'
                    }

            except Exception:
                continue

        return None

    @staticmethod
    async def _detect_traditional(page: Page) -> Optional[Dict[str, Any]]:
        """Detect traditional pagination - UNIVERSAL approach"""

        # Get ALL links and buttons
        all_clickable = await page.query_selector_all('a, button')

        next_candidates = []
        page_number_candidates = []

        for element in all_clickable:
            try:
                is_visible = await element.is_visible()
                if not is_visible:
                    continue

                # Get text content
                text = await element.text_content() or ""
                text_lower = text.lower().strip()
                text_stripped = text.strip()

                # Get attributes for additional checks
                classes = await element.get_attribute('class') or ''
                rel_attr = await element.get_attribute('rel') or ''
                aria_label = await element.get_attribute('aria-label') or ''
                title_attr = await element.get_attribute('title') or ''

                # Check if element is disabled
                aria_disabled = await element.get_attribute('aria-disabled')
                if 'disabled' in classes.lower() or aria_disabled == 'true':
                    continue

                # STRATEGY 1: Check for rel="next" attribute (most reliable)
                if 'next' in rel_attr.lower():
                    next_candidates.append(element)
                    continue

                # STRATEGY 2: Check for "next" text patterns
                next_patterns = ['next', '›', '→', '>>', 'siguiente', 'suivant', 'weiter']
                combined_text = f"{text_lower} {aria_label.lower()} {title_attr.lower()}"
                if any(pattern in combined_text for pattern in next_patterns):
                    next_candidates.append(element)
                    continue

                # STRATEGY 3: Check for arrow/icon class names (for icon-based next buttons)
                icon_patterns = [
                    'arrow', 'chevron', 'angle', 'caret',
                    'next', 'forward', 'right'
                ]
                classes_lower = classes.lower()
                if any(pattern in classes_lower for pattern in icon_patterns):
                    # Check if it's a right-pointing indicator
                    if any(term in classes_lower for term in ['right', 'next', 'forward']):
                        # Get inner HTML to check for icon elements
                        inner_html = await element.inner_html()
                        # Check for icon elements or symbols
                        if any(icon in inner_html.lower() for icon in ['icon', 'arrow', 'chevron', '›', '→', '>']):
                            next_candidates.append(element)
                            continue

                # STRATEGY 4: Check for page numbers (numeric links)
                if text_stripped.isdigit():
                    page_num = int(text_stripped)
                    if page_num > 1 and page_num < 1000:  # Reasonable page number range
                        page_number_candidates.append(element)

            except Exception:
                continue

        # If we found next buttons, prioritize those
        if next_candidates:
            # Prefer elements with rel="next" first
            for candidate in next_candidates:
                rel_attr = await candidate.get_attribute('rel') or ''
                if 'next' in rel_attr.lower():
                    return {
                        'next_element': candidate,
                        'next_text': await candidate.text_content() or 'Next'
                    }

            # Otherwise return first next candidate
            return {
                'next_element': next_candidates[0],
                'next_text': await next_candidates[0].text_content() or 'Next'
            }

        # Fallback: If we have page numbers, click on page 2
        if page_number_candidates:
            # Find page 2 specifically
            for candidate in page_number_candidates:
                text = await candidate.text_content()
                if text and text.strip() == '2':
                    return {
                        'next_element': candidate,
                        'next_text': '2',
                        'type': 'page_number'
                    }

            # Or just return first page number > 1
            return {
                'next_element': page_number_candidates[0],
                'next_text': await page_number_candidates[0].text_content(),
                'type': 'page_number'
            }

        return None

    @staticmethod
    async def _detect_infinite_scroll(page: Page, html: str) -> Optional[Dict[str, Any]]:
        """Detect infinite scroll - UNIVERSAL approach"""

        # Check scroll height ratio
        try:
            scroll_height = await page.evaluate('document.documentElement.scrollHeight')
            viewport_height = await page.evaluate('window.innerHeight')

            # If content is significantly longer than viewport, might have infinite scroll
            if scroll_height > viewport_height * 1.8:
                # Look for infinite scroll indicators in HTML
                scroll_indicators = [
                    'infinite', 'lazy', 'scroll', 'lazyload',
                    'data-lazy', 'intersection', 'observer'
                ]

                html_lower = html.lower()
                found_indicators = [ind for ind in scroll_indicators if ind in html_lower]

                if found_indicators:
                    return {
                        'indicators': found_indicators,
                        'scroll_height': scroll_height,
                        'viewport_height': viewport_height
                    }
        except Exception:
            pass

        return None


class PaginationHandler:
    """Universal pagination handler that works across ANY website"""

    def __init__(
        self,
        max_pages: int = 40,
        scroll_pause_time: float = 2.0,
        max_scroll_attempts: int = 10
    ):
        """
        Args:
            max_pages: Maximum pages to crawl (safety limit)
            scroll_pause_time: Seconds to wait after scrolling
            max_scroll_attempts: Max scroll attempts for infinite scroll
        """
        self.max_pages = max_pages
        self.scroll_pause_time = scroll_pause_time
        self.max_scroll_attempts = max_scroll_attempts

    async def paginate(
        self,
        page: Page,
        pagination_type: PaginationType,
        metadata: Dict[str, Any]
    ) -> List[str]:
        """
        Navigate through all pages and collect HTML content

        Args:
            page: Playwright page object
            pagination_type: Type of pagination detected
            metadata: Pagination metadata from detector

        Returns:
            List of HTML content from all pages
        """
        logger.info(f"  📄 Pagination type: {pagination_type.value}")

        if pagination_type == PaginationType.NONE:
            html = await page.content()
            return [html]

        elif pagination_type == PaginationType.LOAD_MORE:
            return await self._handle_load_more_universal(page, metadata)

        elif pagination_type == PaginationType.TRADITIONAL:
            return await self._handle_traditional_universal(page, metadata)

        elif pagination_type == PaginationType.INFINITE_SCROLL:
            return await self._handle_infinite_scroll_universal(page, metadata)

        return [await page.content()]

    async def _handle_load_more_universal(self, page: Page, metadata: Dict[str, Any]) -> List[str]:
        """Universal 'Load More' handler - works on ANY site"""

        clicks = 0
        previous_count = 0
        no_change_count = 0

        logger.info(f"  📄 Clicking 'Load More' button...")

        while clicks < self.max_pages - 1:
            try:
                # Get current vehicle count
                current_count = await self._count_vehicles_universal(page)

                if clicks == 0:
                    logger.info(f"  📄 Initial: {current_count} vehicles")
                    previous_count = current_count

                # Re-find the load more button (it may have changed)
                load_more_result = await PaginationDetector._detect_load_more(page)

                if not load_more_result:
                    logger.info(f"  ✓ Load More button no longer found")
                    break

                button = load_more_result['button_element']

                # Scroll button into view
                await button.scroll_into_view_if_needed()
                await page.wait_for_timeout(300)  # Reduced from 500ms

                # Click the button
                await button.click()
                clicks += 1

                # Wait for content to load (reduced wait time)
                await page.wait_for_timeout(self.scroll_pause_time * 1000)

                # Wait for network idle (reduced timeout)
                try:
                    await page.wait_for_load_state('networkidle', timeout=3000)  # Reduced from 5000ms
                except PlaywrightTimeout:
                    pass

                # Check if new vehicles loaded
                new_count = await self._count_vehicles_universal(page)

                if new_count > current_count:
                    logger.info(f"  📄 Click {clicks}: {new_count} total vehicles (+{new_count - current_count} new)")
                    previous_count = new_count
                    no_change_count = 0
                else:
                    no_change_count += 1
                    if no_change_count >= 2:
                        logger.info(f"  ✓ No new content after {no_change_count} clicks")
                        break

            except Exception as e:
                logger.error(f"  ⚠️  Error during load more: {str(e)[:80]}")
                break

        # Return final HTML with all loaded content
        return [await page.content()]

    async def _handle_traditional_universal(self, page: Page, metadata: Dict[str, Any]) -> List[str]:
        """Universal traditional pagination handler"""

        all_html = []
        current_page = 1
        first_navigation = True  # Track if this is the first page navigation

        # Get initial content
        html = await page.content()
        all_html.append(html)
        logger.info(f"  📄 Page {current_page}: {page.url}")

        while current_page < self.max_pages:
            try:
                # Wait a bit before checking for next button
                await page.wait_for_timeout(500)  # Reduced from 1000ms

                # Re-detect pagination on current page
                traditional_result = await PaginationDetector._detect_traditional(page)

                if not traditional_result:
                    logger.info(f"  ✓ No more pages (no next button found on page {current_page})")
                    break

                if 'next_element' in traditional_result:
                    next_button = traditional_result['next_element']

                    # Check if next button is disabled
                    is_disabled = await next_button.is_disabled()
                    if is_disabled:
                        logger.info(f"  ✓ Reached last page (next button disabled on page {current_page})")
                        break

                    # Get current URL and HTML to detect if navigation actually happened
                    current_url = page.url
                    current_html = await page.content()

                    # Scroll into view
                    await next_button.scroll_into_view_if_needed()
                    await page.wait_for_timeout(300)  # Reduced from 500ms

                    # Click next
                    try:
                        await next_button.click()
                    except Exception as e:
                        logger.error(f"  ⚠️  Failed to click next button on page {current_page}: {str(e)[:80]}")
                        break

                    current_page += 1

                    # Wait for navigation
                    try:
                        # Wait for URL to change or content to load
                        await page.wait_for_load_state('domcontentloaded', timeout=8000)  # Reduced from 10000ms
                    except PlaywrightTimeout:
                        pass

                    # Additional wait for content
                    await page.wait_for_timeout(1000)  # Reduced from 2000ms

                    # Check if URL changed (some sites use URL-based pagination)
                    new_url = page.url
                    new_html = await page.content()

                    # Detect if we actually navigated to a new page
                    if new_url == current_url and new_html == current_html:
                        logger.info(f"  ✓ No change detected, reached last page (page {current_page - 1})")
                        current_page -= 1  # Revert page count since we didn't actually move
                        break

                    # IMPORTANT: Validate we're still on a pagination page, not a completely different page
                    # Parse URLs to check if path changed
                    from urllib.parse import urlparse

                    current_parsed = urlparse(current_url)
                    new_parsed = urlparse(new_url)

                    # Normalize paths (remove trailing slashes for comparison)
                    current_path = current_parsed.path.rstrip('/') or '/'
                    new_path = new_parsed.path.rstrip('/') or '/'

                    # STRICT CHECK: Ensure we're still on same base path
                    # ALLOW these pagination patterns:
                    #   /inventory/used -> /inventory/used?page=2 ✓ (query param added)
                    #   /inventory/used -> /inventory/used/page/2 ✓ (page segment added)
                    #   /inventory/used/page/2 -> /inventory/used/page/3 ✓ (page number incremented)
                    # REJECT navigation to different sections:
                    #   /inventory/used -> /inventory/new ✗ (changed from 'used' to 'new')
                    #   /inventory/used -> /about-us ✗ (completely different page)

                    # Strategy: Check if new path is a valid extension of current path
                    # OR if they share exact same base path up to pagination segments

                    # Remove pagination segments to get base paths
                    def get_base_path(path):
                        # Remove /page/N, /p/N type segments
                        import re
                        # Remove trailing pagination patterns
                        base = re.sub(r'/page/\d+$', '', path)
                        base = re.sub(r'/p/\d+$', '', base)
                        return base

                    current_base = get_base_path(current_path)
                    new_base = get_base_path(new_path)

                    # SMART PATH VALIDATION WITH FIRST NAVIGATION EXCEPTION
                    # =========================================================
                    # First click can add filters/refinements (e.g., /inventory/new -> /inventory/new/mazda)
                    # After that, path must stay stable

                    if first_navigation:
                        # FIRST NAVIGATION: Allow path refinements but check we're still in same section
                        # Example GOOD: /inventory/new -> /inventory/new/mazda?filters ✓
                        # Example BAD:  /inventory/new -> /about-us ✗

                        # Check if new path is extension of current (refinement)
                        is_refinement = new_base.startswith(current_base)

                        # Must share at least first 2 path segments (inventory section)
                        current_parts = [p for p in current_base.split('/') if p]
                        new_parts = [p for p in new_base.split('/') if p]

                        shares_section = (
                            len(current_parts) >= 2 and
                            len(new_parts) >= 2 and
                            current_parts[0] == new_parts[0] and  # e.g., 'inventory'
                            current_parts[1] == new_parts[1]      # e.g., 'new' or 'used'
                        )

                        if not is_refinement or not shares_section:
                            logger.info(f"  ✓ First click went to different section, stopping")
                            logger.info(f"     Original: {current_base}")
                            logger.info(f"     New: {new_base}")
                            current_page -= 1
                            break

                        # First navigation successful
                        first_navigation = False
                        if current_base != new_base:
                            logger.info(f"  ℹ️  Path refined on first navigation: {current_base} → {new_base}")

                    else:
                        # SUBSEQUENT NAVIGATIONS: Strict - path must stay exactly same
                        is_valid_pagination = (
                            (current_base == new_base) or  # Same base path
                            (new_path.startswith(current_base + '/page/')) or  # Added /page/N
                            (new_path.startswith(current_base + '/p/'))  # Added /p/N
                        )

                        # If query params changed, base path must match exactly
                        if current_parsed.query != new_parsed.query:
                            if current_base != new_base:
                                is_valid_pagination = False

                        if not is_valid_pagination:
                            logger.info(f"  ✓ Path changed after pagination started, stopping")
                            logger.info(f"     Expected: {current_base}")
                            logger.info(f"     Got: {new_base}")
                            current_page -= 1
                            break

                    if new_url != current_url:
                        logger.info(f"  📄 Page {current_page}: {new_url[:70]}")
                    else:
                        logger.info(f"  📄 Page {current_page}: (content updated)")

                    # Get new page content
                    all_html.append(new_html)

                else:
                    logger.info(f"  ✓ No next button found on page {current_page}")
                    break

            except Exception as e:
                logger.error(f"  ⚠️  Error navigating from page {current_page}: {str(e)[:80]}")
                break

        logger.info(f"  ✓ Navigated through {len(all_html)} page(s)")
        return all_html

    async def _handle_infinite_scroll_universal(self, page: Page, metadata: Dict[str, Any]) -> List[str]:
        """Universal infinite scroll handler"""

        scroll_attempts = 0
        previous_count = 0
        no_change_count = 0

        logger.info(f"  📄 Scrolling to load content...")

        while scroll_attempts < self.max_scroll_attempts:
            # Get current count
            current_count = await self._count_vehicles_universal(page)

            if scroll_attempts == 0:
                print(f"  📄 Initial: {current_count} vehicles")
                previous_count = current_count

            # Scroll to bottom
            await page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)')

            # Wait for content
            await page.wait_for_timeout(self.scroll_pause_time * 1000)

            try:
                await page.wait_for_load_state('networkidle', timeout=2000)  # Reduced from 3000ms
            except PlaywrightTimeout:
                pass

            # Check new count
            new_count = await self._count_vehicles_universal(page)

            if new_count > current_count:
                logger.info(f"  📄 Scroll {scroll_attempts + 1}: {new_count} total (+{new_count - current_count} new)")
                no_change_count = 0
                previous_count = new_count
            else:
                no_change_count += 1
                if no_change_count >= 3:
                    logger.info(f"  ✓ No new content after {no_change_count} scrolls")
                    break

            scroll_attempts += 1

        return [await page.content()]

    async def _count_vehicles_universal(self, page: Page) -> int:
        """
        Universal vehicle counter - works across ANY dealership site
        Uses multiple strategies to find vehicle cards/listings
        """

        # Strategy 1: Common vehicle selectors
        vehicle_selectors = [
            '[data-vehicle-id]',
            '[data-vin]',
            '[data-stock]',
            '[class*="vehicle-card"]',
            '[class*="vehicle-item"]',
            '[class*="inventory-item"]',
            '[class*="car-card"]',
            '[class*="listing"]',
            '[class*="result"]',
            'article[class*="vehicle"]',
            'div[class*="vehicle"][class*="card"]',
            '.vehicle',
            '.car-item',
            '.inventory-vehicle',
        ]

        max_count = 0
        for selector in vehicle_selectors:
            try:
                count = await page.locator(selector).count()
                max_count = max(max_count, count)
            except Exception:
                continue

        # Strategy 2: If no selectors match, try to find repeating elements
        if max_count == 0:
            try:
                # Look for article tags (common for listings)
                articles = await page.locator('article').count()
                max_count = max(max_count, articles)

                # Look for divs with similar classes that repeat
                # This is a heuristic approach
            except Exception:
                pass

        return max_count

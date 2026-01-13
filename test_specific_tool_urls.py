#!/usr/bin/env python3
"""
Test specific URLs for tool detection
Bypasses URL seeding and classification entirely
"""
import os
import asyncio
import random
from typing import Dict, Any
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig
from dealership_scraper.models import ToolType
from dealership_scraper.detectors import ToolDetector


async def test_specific_urls():
    """Test tool detection on specific URLs"""
    API_KEY = os.getenv("OPENAI_API_KEY")

    if not API_KEY:
        print("❌ Error: OPENAI_API_KEY not set")
        return

    # ============================================
    # CUSTOMIZE THESE URLS
    # ============================================
    URLS_TO_TEST = [
        "https://www.cardinalenissan.com/pre-qual",
        # "https://www.cardinalenissan.com/getfinancing",
        # Add more URLs here:
        # "https://www.cardinalenissan.com/another-page",
    ]

    DETECTION_STRICTNESS = "lenient"  # "strict" or "lenient"
    # ============================================

    print("\n" + "="*80)
    print("SPECIFIC URL TOOL DETECTION")
    print("="*80)
    print(f"Testing {len(URLS_TO_TEST)} URL(s)")
    print(f"Detection Mode: {DETECTION_STRICTNESS.upper()}")
    print("="*80 + "\n")

    # Initialize detector
    tool_detector = ToolDetector(API_KEY, strictness=DETECTION_STRICTNESS)

    # Track best findings for each tool
    tool_results = {tool.value: {
        "isPresent": False,
        "url": None,
        "notes": "Not found",
        "confidence": 0.0,
        "evidence": "",
        "location": ""
    } for tool in ToolType}

    browser_config = BrowserConfig(headless=False, verbose=False)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for i, url in enumerate(URLS_TO_TEST, 1):
            # Smart delay for popup pages
            delay = get_smart_delay(url)
            print(f"\n[{i}/{len(URLS_TO_TEST)}] Processing: {url}")
            print(f"  Delay: {delay}s")

            # Use domcontentloaded - more reliable than networkidle
            # The delay_before_return_html gives JS/popups time to load
            result = await crawler.arun(
                url,
                config=CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    wait_until="domcontentloaded",  # Wait for DOM load
                    page_timeout=30000,
                    delay_before_return_html=delay,  # Smart delay for popups/JS
                    wait_for_images=False
                )
            )

            try:
                if not result.success:
                    print(f"  ✗ Failed to load")
                    continue

                # Get markdown text
                markdown = str(result.markdown) if hasattr(result, 'markdown') and result.markdown else ""

                # Check for popup
                has_popup = detect_popup_in_html(result.html)
                if has_popup:
                    print(f"  ⚠️  Popup detected on page")

                # Save debug files
                save_page_debug(url, result.html, markdown, i)
                print(f"  💾 Debug files saved to output/debug/")

                # Detect tools
                detections = await tool_detector.detect(url, result.html, markdown)

                # Update results with best findings
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
                    print(f"  ✅ Found: {', '.join(found_tools)}")
                else:
                    print(f"  - No new tools found")

                await asyncio.sleep(random.uniform(1.0, 2.0))

            except Exception as e:
                print(f"  ✗ Error: {str(e)[:50]}")

    # Print summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)

    detected_count = sum(1 for t in tool_results.values() if t["isPresent"])
    print(f"\n✓ Detected {detected_count}/8 tools\n")

    for tool_name, data in tool_results.items():
        status = "✅" if data["isPresent"] else "❌"
        confidence = data["confidence"]
        url = data["url"] or "N/A"
        print(f"{status} {tool_name:30s} | Confidence: {confidence:.2f} | {url}")

    # Save results
    import json
    os.makedirs("output", exist_ok=True)

    tools_output = [
        {
            "tool_name": name,
            "isPresent": data["isPresent"],
            "confidence": data.get("confidence", 0.0),
            "url": data.get("url") or "",
            "evidence": data.get("evidence", ""),
            "location": data.get("location", ""),
            "notes": data.get("notes", "")
        }
        for name, data in tool_results.items()
    ]

    with open("output/tools.json", "w", encoding="utf-8") as f:
        json.dump(tools_output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved: output/tools.json")
    print(f"✓ Debug files: output/debug/")
    print("\n" + "="*80)


def get_smart_delay(url: str) -> float:
    """
    Determine delay after networkidle

    Since we use wait_until="networkidle", the crawler already waits for
    network activity to settle. This additional delay gives time for any
    post-load animations or delayed popups.
    """
    import re

    # URLs that commonly have delayed popups (after network is idle)
    delayed_popup_patterns = [
        r'/pre[-_]?qual',
        r'/get[-_]?financing',
        r'/apply',
        r'/credit[-_]?app',
        r'/finance',
        r'/trade[-_]?in',
        r'/value[-_]?trade',
        r'/specials',
        r'/calculator',
    ]

    url_lower = url.lower()
    for pattern in delayed_popup_patterns:
        if re.search(pattern, url_lower):
            return 3.0  # Extra 3s for delayed popups (networkidle already waited)

    return 1.0  # Just 1s for normal pages (networkidle already waited)


def detect_popup_in_html(html: str) -> bool:
    """Detect if HTML contains popup indicators"""
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


def save_page_debug(url: str, html: str, markdown: str, index: int):
    """Save page HTML and markdown for debugging"""
    import re

    safe_url = re.sub(r'[^\w\-]', '_', url.replace('https://', '').replace('http://', ''))
    safe_url = safe_url[:100]

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
    iframes = re.findall(r'<iframe[^>]*src=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE)
    if iframes:
        iframe_file = f"{debug_dir}/{index:03d}_{safe_url}_iframes.txt"
        with open(iframe_file, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\n")
            f.write(f"Found {len(iframes)} iframe(s):\n\n")
            for iframe_url in iframes:
                f.write(f"  - {iframe_url}\n")


if __name__ == "__main__":
    asyncio.run(test_specific_urls())

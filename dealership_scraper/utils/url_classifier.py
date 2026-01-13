"""
Unified URL Classifier
Classifies dealership URLs into VDP, SRP, and Finance categories in a single pass
Uses parallel API calls for faster classification
"""
import os
import asyncio
from typing import List, Dict
from openai import AsyncOpenAI
from pydantic import BaseModel
from urllib.parse import urlparse
import logging

class URLClassificationItem(BaseModel):
    """Single URL classification result"""
    url: str
    type: str
    confidence: float  # 0.0 to 1.0


class URLClassificationResponse(BaseModel):
    """Response model for batch URL classification"""
    urls: List[URLClassificationItem]


async def classify_urls(
    urls: List[str],
    domain: str,
    batch_size: int = 30
) -> Dict[str, List[str]]:
    """
    Classify URLs into VDP, SRP, and Finance categories
    Automatically adds homepage to the finance list

    Args:
        urls: List of URLs to classify
        domain: Main domain URL (for homepage detection)
        batch_size: Number of URLs to process per API call

    Returns:
        Dict with keys: vdp, srp, finance, other
    """
    # Detect and add homepage
    homepage_url = _extract_homepage(domain)

    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )

    # Get unified prompts
    categories, system_prompt, user_prompt_template = _get_unified_prompts()

    # Initialize results dict
    classified_with_scores = {cat: [] for cat in categories}

    # Add homepage to finance list with high confidence
    if homepage_url:
        classified_with_scores["finance"].append((homepage_url, 1.0))

    # Split URLs into batches and create tasks
    batches = []
    for i in range(0, len(urls), batch_size):
        batches.append(urls[i:i + batch_size])

    logging.info(f"Classifying {len(urls)} URLs in {len(batches)} batches (parallel)")

    # Create parallel tasks for all batches
    tasks = [
        _classify_batch(client, batch, i, system_prompt, user_prompt_template)
        for i, batch in enumerate(batches)
    ]

    # Execute all tasks in parallel
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results from all batches
    for batch_idx, result in enumerate(batch_results):
        if isinstance(result, Exception):
            logging.error(f"Batch {batch_idx} failed: {str(result)[:80]}")
            # Fallback: mark all URLs in this batch as other
            for url in batches[batch_idx]:
                classified_with_scores["other"].append((url, 0.0))
        else:
            # Merge results from this batch
            for url_type, url_list in result.items():
                if url_type in classified_with_scores:
                    classified_with_scores[url_type].extend(url_list)

    # Sort by confidence (highest first) and extract URLs
    classified = {
        cat: [url for url, conf in sorted(urls_with_scores, key=lambda x: x[1], reverse=True)]
        for cat, urls_with_scores in classified_with_scores.items()
    }

    return classified


async def _classify_batch(
    client: AsyncOpenAI,
    batch: List[str],
    batch_idx: int,
    system_prompt: str,
    user_prompt_template: str
) -> Dict[str, List[tuple]]:
    """Classify a single batch of URLs"""
    import json

    url_list = "\n".join([f"{j+1}. {url}" for j, url in enumerate(batch)])
    prompt = user_prompt_template.format(url_list=url_list)

    try:
        logging.info(f"Batch {batch_idx}: Starting classification of {len(batch)} URLs")

        response = await client.beta.chat.completions.parse(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format=URLClassificationResponse,
            temperature=0.0,
            prompt_cache_retention="24h"
        )

        # Parse structured output
        parsed_response = response.choices[0].message.parsed

        logging.info(f"Batch {batch_idx}: Completed classification")

        # Process classifications with structured output
        batch_results = {"vdp": [], "srp": [], "finance": [], "other": []}

        for item in parsed_response.urls:
            url_type = item.type.lower()
            confidence = max(0.0, min(1.0, item.confidence))

            if url_type in batch_results:
                batch_results[url_type].append((item.url, confidence))
            else:
                batch_results["other"].append((item.url, confidence))

        return batch_results

    except Exception as e:
        logging.error(f"Batch {batch_idx} failed: {str(e)[:80]}")
        raise


def _extract_homepage(domain: str) -> str:
    """Extract clean homepage URL from domain"""
    # Remove protocol if present
    clean_domain = domain.replace('https://', '').replace('http://', '').rstrip('/')
    # Return with https://
    return f"https://{clean_domain}"


def _get_unified_prompts():
    """Get unified prompts for VDP, SRP, and Finance classification"""
    categories = ["vdp", "srp", "finance", "other"]

    system_prompt = """You are an expert car dealership URL classifier. Classify URLs into VDP (single vehicle), SRP (multiple vehicles), FINANCE (tools/calculators), or OTHER. Return ONLY valid JSON."""

    user_prompt_template = """Classify car dealership URLs into 4 categories: VDP, SRP, FINANCE, or OTHER.

═══════════════════════════════════════════════════════════════════

✓ CATEOGORIES OF CARS/INVENTORY TO LOOK FOR:
  • new, used, certified pre-owned vehicles
  • sedan,truck,suv,coupe,hatchback,minivan

**CATEGORY 1: VDP (Vehicle Detail Page)**
Shows a SINGLE specific vehicle with full details.

✓ MUST HAVE indicators:
  • Unique identifier in URL: VIN (17 alphanumeric chars), stock number, or numeric vehicle ID
  • URL patterns: /inventory/12345, /vehicle/ABC123, /vdp/stock-789, /details/VIN1234567890ABCDE, /viewdetail/vin1234567890ABCDE

✓ VIN DETECTION RULES:
  • VIN is EXACTLY 17 alphanumeric characters (no dashes, no spaces)
  • Must be in URL path or as a query parameter
  • Examples: VIN123456789ABCDEF, 1HGCV1F16NA123456

✓ STOCK/ID DETECTION RULES:
  • Numeric IDs: /inventory/12345, /vehicle/67890
  • Alphanumeric stock: /stock/ABC123, /vdp/stock-A789
  • NOT make/model names: ford, expedition-max, camry, accord are NOT stock numbers

✓ Examples of VDP:
  • https://dealer.com/inventory/used-2023-honda-accord-1HGCV1F16NA123456 (has 17-char VIN)
  • https://dealer.com/vehicle/12345/2024-toyota-camry (has numeric ID: 12345)
  • https://dealer.com/vdp/stock-A789456 (has stock number)
  • https://dealer.com/details/new/1HGCV1F16NA123456 (has VIN)
  • https://dealer.com/inventory/12345 (has numeric ID)

✗ NOT VDP (these are SRP - Search Results / Filtered Listings):
  • /inventory (no specific ID)
  • /new-vehicles (listing page)
  • /inventory/used/ford/expedition-max (make/model filter, NOT a VIN or stock)
  • /inventory/new/toyota (brand filter)
  • /inventory/suv (type filter)
  • /used/honda/accord (make/model filter)
  • /new/trucks (category filter)

**Confidence Scoring for VDP:**
  • 0.95-1.0:  Clear VIN or stock number in URL
  • 0.80-0.94: Vehicle-specific path with ID (like /inventory/12345)
  • 0.60-0.79: Likely detail page structure but less clear
  • <0.60:     Uncertain, might not be VDP

═══════════════════════════════════════════════════════════════════

**CATEGORY 2: SRP (Search Results Page)**
Shows MULTIPLE vehicles in a grid/list format.

✓ MUST SHOW: Multiple vehicle listings on one page

✓ PRIORITY (Best for payment detection):
  1. Main inventory pages (HIGHEST): /inventory, /new-inventory, /used-inventory, /cpo, /certified, /used, /new
  2. Category pages (HIGH): /inventory/new, /inventory/used, /new-vehicles
  3. Make/Model filtered pages (HIGH): /inventory/used/ford, /inventory/new/toyota/camry, /used/honda/accord
  4. Type filtered pages (HIGH): /inventory/suv, /new/trucks, /used/sedans
  5. Query filtered pages (MEDIUM): /inventory?make=Honda, /search?type=suv
  6. Paginated results (MEDIUM): /inventory/page/2, /inventory?page=3

✓ Examples of SRP:
  • https://dealer.com/inventory
  • https://dealer.com/new-inventory
  • https://dealer.com/inventory/new
  • https://dealer.com/vehicles/used
  • https://dealer.com/inventory/used/ford/expedition-max (make/model filter)
  • https://dealer.com/used/honda/accord (make/model filter)
  • https://dealer.com/new/toyota (brand filter)
  • https://dealer.com/inventory/suv (type filter)
  • https://dealer.com/search?make=Toyota&year=2024
  • https://dealer.com/inventory?type=new&page=2

✗ AVOID (Lower confidence):
  • URLs with cash-only filters: ?payment=cash
  • Overly specific filters that might have few results
  • URLs that look like detail pages (with VIN or numeric ID)

**Confidence Scoring for SRP:**
  • 0.95-1.0:  Main inventory page (exact: /inventory, /new-inventory, /used-inventory)
  • 0.85-0.94: Category pages (/inventory/new, /new-vehicles, /used, /new, /cpo, /certified)
  • 0.80-0.89: Make/Model filtered (/inventory/used/ford, /new/toyota/camry, /inventory/used/ford/expedition-max)
  • 0.75-0.84: Type filtered (/inventory/suv, /new/trucks, /used/sedans)
  • 0.70-0.79: Query filtered with common filters (make, model, year)
  • 0.50-0.69: Paginated or heavily filtered listings
  • 0.30-0.49: Uncertain or cash-only filters
  • <0.30:     Likely not a good inventory page

═══════════════════════════════════════════════════════════════════

**CATEGORY 3: FINANCE**
Pages with dealership tools (calculators, applications, payment estimators).

✓ MUST HAVE indicators:
  • Finance keywords: finance, financing, payment, apply, credit, lease
  • Calculator keywords: calculator, estimate, estimator, payment-calc
  • Application keywords: get-approved, pre-qualify, credit-app
  • Trade-in keywords: value-your-trade, trade-in, appraisal
  • Specials keywords: specials, offers, incentives, deals

✓ Examples of FINANCE:
  • https://dealer.com/finance
  • https://dealer.com/financing/payment-calculator
  • https://dealer.com/apply-for-credit
  • https://dealer.com/value-your-trade
  • https://dealer.com/special-offers

**Confidence Scoring for FINANCE:**
  • 0.90-1.0:  Clear finance/tool keywords
  • 0.70-0.89: Related keywords (specials, offers)
  • 0.50-0.69: Possible tool page

═══════════════════════════════════════════════════════════════════

**CATEGORY 4: OTHER**
Everything else (about, service, contact, etc).

✓ Examples:
  • About/Info: /about-us, /contact, /hours
  • Service: /service, /parts, /maintenance
  • Resources: /reviews, /blog, /careers

**Confidence Scoring for OTHER:**
  • 0.0-0.2: Clearly not relevant

═══════════════════════════════════════════════════════════════════

**DECISION RULES:**

1. **VDP Detection (STRICT):**
   - URL MUST contain a 17-character VIN (alphanumeric only)
   - OR URL MUST contain a numeric ID (e.g., /inventory/12345, /vehicle/67890)
   - OR URL MUST contain "stock" or "vdp" with alphanumeric ID
   - Make/model names (ford, honda, camry, expedition-max, etc.) are NOT VINs or IDs

2. **SRP Detection:**
   - Main inventory paths: /inventory, /vehicles, /new-inventory, /used-inventory
   - Category paths: /inventory/new, /inventory/used, /new, /used, /cpo, /certified
   - Filtered paths with make/model: /inventory/used/ford/expedition-max, /new/toyota/camry
   - Type filters: /inventory/suv, /new/trucks
   - If it shows multiple vehicles (listing/search page) → SRP

3. **FINANCE Detection:**
   - URL has finance/calculator/tools keywords → FINANCE

4. **OTHER Detection:**
   - URL is about/service/contact → OTHER

**CRITICAL: Make vs Model vs VIN/Stock:**
- Make names: ford, toyota, honda, chevrolet, nissan → SRP (filter)
- Model names: camry, accord, expedition-max, f-150, silverado → SRP (filter)
- VINs: 1HGCV1F16NA123456 (17 chars) → VDP (unique identifier)
- Stock/IDs: 12345, ABC123, stock-A789 → VDP (unique identifier)

═══════════════════════════════════════════════════════════════════

**URLs TO CLASSIFY:**
{url_list}

For each URL, determine:
1. type: "vdp", "srp", "finance", or "other"
2. confidence: Float between 0.0 and 1.0"""

    return categories, system_prompt, user_prompt_template

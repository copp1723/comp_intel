"""
Tool Detection Module
Detects 8 dealership tools using LLM analysis
"""
import re
import json
import asyncio
import logging
from typing import List, Dict, Any
from openai import OpenAI
from ..models import ToolDetection, ToolType

# Get logger
logger = logging.getLogger(__name__)


class ToolDetector:
    """Detects dealership tools on webpages"""

    def __init__(self, api_key: str, strictness: str = "lenient", enable_parallel: bool = False, max_workers: int = 3):
        """
        Initialize tool detector

        Args:
            api_key: OpenAI API key
            strictness: Detection mode - "strict" or "lenient" (default: "lenient")
            enable_parallel: Enable parallel processing of URLs (default: False)
            max_workers: Maximum parallel workers (default: 3)
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.strictness = strictness
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers

    def clean_html(self, html: str) -> str:
        """Clean HTML for analysis"""
        # Extract iframe information before removing scripts
        iframes = re.findall(r'<iframe[^>]*src=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE)
        iframe_info = ""
        if iframes:
            iframe_info = "\n\n<!-- IFRAMES DETECTED:\n"
            for iframe_url in iframes:
                iframe_info += f"  - {iframe_url}\n"
            iframe_info += "-->\n"

        # Remove scripts and styles
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Add iframe info at the top
        html = iframe_info + html
        return html[:12000]  # Keep first 12k chars

    def clean_text(self, text: str) -> str:
        """Clean markdown text"""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text[:4000]  # Keep first 4k chars

    def get_prompt(self, url: str, html_clean: str, text_clean: str) -> str:
        """Generate detection prompt based on strictness setting"""

        if self.strictness == "strict":
            return f"""Analyze this dealership page for 8 tools. Be STRICT - require INTERACTIVE tools with actual functionality.

URL: {url}

HTML (check for <input>, <form>, <select>, <button> tags, iframes):
{html_clean}

TEXT:
{text_clean}

CRITICAL RULES:
- Navigation links to tools DO NOT count as tool presence
- Tools CAN be on homepage IF they are INTERACTIVE (forms, inputs, iframes) on the homepage itself
- Require actual INTERACTIVE elements (forms, inputs, iframes) - NOT just navigation links
- If homepage only has nav menu items pointing to tool pages → tools are NOT present

═══════════════════════════════════════════════════════════════════

1. **payment_calculator**
   WHAT IT IS: Interactive tool that lets users input price, down payment, term, APR and see monthly payment.

   ✓ MUST HAVE (at least one):
   - Form with <input> fields for: price, down payment, term, APR + calculate button
   - "Calculate Payment" button that opens interactive drawer/popup/panel with inputs
   - Third-party iframe (Dealertrack, RouteOne) with payment calculation form
   - Widget/calculator embedded on page (even if on homepage)

   ✓ VALID ON HOMEPAGE:
   - Calculator widget with input fields visible on homepage
   - "Calculate Payment" button that opens modal with actual form
   - Embedded iframe calculator on homepage

   ✗ FALSE POSITIVES (reject these):
   - Navigation link to "/payment-calculator" without actual form on THIS page
   - "Payment Calculator" menu item only (no actual calculator)
   - Static "payment example" text
   - PDF with finance offers
   - "Calculate Payment" text without interactive elements

   KEYWORDS TO LOOK FOR: calculate, estimate, payment together + form fields (price, down payment, term, APR)

═══════════════════════════════════════════════════════════════════

2. **apr_disclosure**
   WHAT IT IS: Text clearly stating specific APR rates with legal fine print.

   ✓ MUST HAVE:
   - Specific numbers: "2.9% APR", "0% APR for 60 months", "6.9% financing"
   - Pattern: X% APR near "months" or "term" or "well-qualified"

   ✓ VALID ON HOMEPAGE:
   - Current financing offers displayed on homepage with specific APR rates
   - Banner/hero section showing "0% APR for 60 months" with details
   - Promotional offers with actual rate numbers

   ✗ FALSE POSITIVES (reject these):
   - Generic "financing available" without rates
   - "0% financing" if it's just a nav link text (must be actual offer with numbers)
   - Bank disclosures not connected to vehicles
   - "Financing" menu item without actual rates shown

   KEYWORDS: % APR, APR, Annual Percentage Rate, X% financing + "months"/"term"

═══════════════════════════════════════════════════════════════════

3. **lease_payment_options**
   WHAT IT IS: Clearly labeled lease option or monthly lease payment as alternative to finance.

   ✓ MUST HAVE:
   - Specific lease amounts: "Lease for $299/mo for 36 months"
   - "$279/month with $2,999 due at signing"
   - Finance/Lease/Cash tabs or toggles on THIS page

   ✗ FALSE POSITIVES (reject these):
   - "Leasing" mentioned in FAQ without actual lease offers
   - Nav link to lease page without offers on THIS page
   - Finance-only examples with no "lease" wording

   KEYWORDS: lease, lease for $, per month lease + actual dollar amounts + months

═══════════════════════════════════════════════════════════════════

4. **pre_qualification_tool**
   WHAT IT IS: Lightweight form for pre-qualifying (soft credit pull), SHORTER than full application.

   ✓ MUST HAVE:
   - Form with keywords: "pre-qualify", "prequalified", "preapproval", "get pre-approved"
   - Language: "soft pull", "no credit impact", "check your buying power"
   - FEW fields (name, contact, maybe income) - NOT full SSN/DOB
   - Third-party iframe from finance partners

   ✓ VALID ON HOMEPAGE:
   - Pre-qualification form/widget embedded on homepage
   - "Get Pre-Qualified" button that opens modal with actual form
   - Embedded iframe for pre-qual on homepage

   ✗ FALSE POSITIVES (reject these):
   - Full finance application with SSN/DOB (that's #6)
   - Generic contact forms "Contact us for financing"
   - Navigation link without actual form on THIS page
   - "Get Pre-Qualified" menu item only (no actual form)

   KEYWORDS: pre-qualify, prequalified, preapproval, get pre-approved + form with limited fields

═══════════════════════════════════════════════════════════════════

5. **trade_in_tool**
   WHAT IT IS: Tool to estimate customer's trade-in value.

   ✓ MUST HAVE:
   - Form asking for CURRENT vehicle: year, make, model, mileage + contact
   - Buttons: "Value Your Trade", "Trade-In Appraisal", "What's My Car Worth?"
   - Third-party iframe (KBB, Black Book, TradePending)
   - URLs: /value-your-trade, /trade-in, /tradeappraisal

   ✓ VALID ON HOMEPAGE:
   - Trade-in widget/form embedded on homepage
   - "Value Your Trade" button that opens modal with actual form
   - KBB/Black Book iframe embedded on homepage

   ✗ FALSE POSITIVES (reject these):
   - Blog post "How to Trade-In Your Car" (informational only)
   - Generic contact form "Ask us about trade-ins"
   - Nav link without actual form on THIS page
   - "Value Your Trade" menu item only (no actual tool)

   KEYWORDS: trade, trade-in, value your trade, trade appraisal + form with vehicle details

═══════════════════════════════════════════════════════════════════

6. **online_finance_application**
   WHAT IT IS: Full credit/finance application that can be submitted online.

   ✓ MUST HAVE:
   - Form with fields: date of birth, SSN (or national ID), employment, income, housing
   - Keywords: "credit application", "finance application", "apply for financing"
   - Multi-step wizard or long form
   - Third-party iframe from finance companies

   ✓ VALID ON HOMEPAGE:
   - Finance application form embedded on homepage
   - "Apply for Financing" button that opens modal with full application
   - Embedded iframe for credit application on homepage

   ✗ FALSE POSITIVES (reject these):
   - Contact forms with only name/phone/email
   - PDF application to download and print
   - Pre-qualification forms (that's #4)
   - "Apply for Financing" menu item only (no actual form)

   KEYWORDS: credit application, finance application, apply for financing + form with SSN/DOB/employment

═══════════════════════════════════════════════════════════════════

7. **srp_payments_shown** (Search Results Page)
   WHAT IT IS: Listing page with MULTIPLE cars showing monthly payments (not just prices).

   ✓ MUST HAVE:
   - MULTIPLE vehicles displayed on THIS page
   - Payments VISIBLE: "$/mo", "per month", "$399/mo" on vehicle cards
   - NOT behind "Calculate" buttons

   ✗ FALSE POSITIVES (reject these):
   - Only total price ($25,990) without /mo
   - "As low as $X" without /month or /mo
   - Single vehicle (that's VDP, not SRP)
   - Payments hidden behind clicks

   KEYWORDS: $/mo, per month, per mo + MULTIPLE vehicles on page

═══════════════════════════════════════════════════════════════════

8. **vdp_payments_shown** (Vehicle Detail Page)
   WHAT IT IS: Page dedicated to SINGLE car showing monthly payment.

   ✓ MUST HAVE:
   - SINGLE specific vehicle on page
   - Payment VISIBLE: "$379/mo", "Estimated payment: $X/mo"
   - Main pricing box or finance section with payment

   ✗ FALSE POSITIVES (reject these):
   - Payment hidden behind "Calculate" button (must click to see)
   - Only price without payment
   - Payment in image/banner graphic (hard to detect, skip if uncertain)
   - Multiple vehicles (that's SRP)

   KEYWORDS: $[digits]/mo, per month + SINGLE vehicle

═══════════════════════════════════════════════════════════════════

DETECTION RULES:
1. For tools 1, 4, 5, 6: Require actual FORM ELEMENTS in HTML (<input>, <select>, <form>, <iframe>)
2. For tools 2, 3: Require actual OFFER TEXT with specific numbers on THIS page
3. For tools 7, 8: Payments must be VISIBLE in text, not hidden behind interactions
4. Navigation links DO NOT count - tool must be functional on THIS page
5. Tools CAN be on homepage if interactive elements exist (e.g., calculator widget, embedded forms)
6. When uncertain: isPresent=false, confidence<0.5

CONFIDENCE SCORING:
- 0.9-1.0: Clear form elements or specific payment numbers visible
- 0.7-0.89: Strong keywords + likely functional
- 0.5-0.69: Uncertain, some indicators but not definitive
- <0.5: Missing or only navigation links

Return JSON:
{{
  "tools": [
    {{
      "tool_name": "payment_calculator",
      "isPresent": true/false,
      "confidence": 0.0-1.0,
      "evidence": "Quote exact HTML/text found or 'Not found'",
      "location": "navigation/main/sidebar/footer",
      "url": "{url}",
      "notes": "Brief reason - mention if only nav link detected"
    }},
    // ... all 8 tools
  ]
}}"""

        else:  # lenient mode (default)
            return f"""Analyze this dealership page for 8 tools. Be PRACTICAL and focus on user-facing functionality.

URL: {url}

HTML (check for <input>, <form>, <select>, <button> tags):
{html_clean}

TEXT:
{text_clean}

**IMPORTANT: Check HTML for "IFRAMES DETECTED" comment at the top. Third-party iframes (RouteOne, DealerSocket, KBB, etc.) indicate tools are present even if form fields aren't visible.**

DETECT THESE 8 TOOLS (be less strict - if it looks like it works, count it):

1. **payment_calculator**
   ✓ Count as YES if:
   - Interactive calculator with inputs (price, down payment, term, APR)
   - Calculator button/widget that opens payment tool
   - Plugin/iframe that provides payment calculation
   - "Calculate Payment" button that works (even if via modal/popup)
   ✗ Only reject if:
   - Just static text with no interactivity
   - Only links to external bank calculators

2. **apr_disclosure**
   ✓ Count as YES if:
   - Any mention of specific APR rates (e.g., "2.9% APR", "0% financing")
   - Current financing offers with rates
   - APR in disclaimers if tied to actual offers
   ✗ Only reject if:
   - No APR mentioned anywhere
   - Only generic "rates vary" without numbers

3. **lease_payment_options**
   ✓ Count as YES if:
   - Specific lease amounts mentioned (e.g., "$299/mo")
   - Lease specials with payment details
   - Current lease offers
   ✗ Only reject if:
   - Only generic "leasing available" without any amounts
   - No lease information at all

4. **pre_qualification_tool**
   ✓ Count as YES if:
   - Pre-qualification or pre-approval form (soft credit check)
   - "Get Pre-Qualified" button/form with basic info
   - Mentions "no impact to credit" or "soft pull"
   - Simple qualification form (doesn't need full SSN)
   - **IFRAME from third-party pre-qual provider (e.g., RouteOne, DealerSocket, etc.)**
   - Check HTML comments for IFRAMES DETECTED section
   ✗ Only reject if:
   - Full credit application (that's #6)
   - No qualification option

5. **trade_in_tool**
   ✓ Count as YES if:
   - Trade-in value estimator/form
   - "Value Your Trade" tool
   - Form asking for vehicle info (year/make/model)
   - Link/button to trade-in appraisal tool
   - **IFRAME from third-party trade-in provider (e.g., KBB, Edmunds, BlackBook)**
   - Check HTML comments for IFRAMES DETECTED section
   ✗ Only reject if:
   - Only informational content about trade-ins
   - No interactive trade-in tool

6. **online_finance_application**
   ✓ Count as YES if:
   - Full finance/credit application
   - Form with detailed personal info (SSN, DOB, employment)
   - "Apply for Financing" form
   - Online credit application
   - **IFRAME from third-party finance provider (e.g., RouteOne, DealerTrack, etc.)**
   - Check HTML comments for IFRAMES DETECTED section
   ✗ Only reject if:
   - Only simple contact forms
   - No finance application available

7. **srp_payments_shown**
   ✓ Count as YES if:
   - Multiple vehicles listed with payment amounts visible
   - "$XXX/mo" shown on vehicle cards/tiles
   - Payment info displayed without clicking (even if small print)
   - "See Payment Options" buttons that reveal payments on same page
   ✗ Only reject if:
   - No payment information at all on listings
   - Must go to VDP to see any payment info
   - Only shows prices, no payments

8. **vdp_payments_shown**
   ✓ Count as YES if:
   - Single vehicle page with payment amount visible
   - "$XXX/mo" displayed on page
   - Payment visible without interaction
   - Payment shown in collapsed section that user can expand
   ✗ Only reject if:
   - No payment shown anywhere
   - Must use calculator to see payment

IMPORTANT RULES:
- Be PRACTICAL: If a tool exists and users can access it, count it as present
- Interactive tools behind buttons/modals still count (as long as they work)
- Tools in iframes/plugins count if functional
- Focus on whether the functionality EXISTS, not how perfectly it's implemented
- Confidence 0.7+ if you see clear evidence
- Confidence 0.5-0.7 if likely present but not 100% certain
- Confidence <0.5 only if very unclear or missing

Return JSON:
{{
  "tools": [
    {{
      "tool_name": "payment_calculator",
      "isPresent": true/false,
      "confidence": 0.0-1.0,
      "evidence": "Quote HTML/text found or 'Not found'",
      "location": "navigation/main/sidebar/footer",
      "url": "{url}",
      "notes": "Brief reason"
    }},
    // ... all 8 tools
  ]
}}"""

    async def detect(self, url: str, html: str, markdown: str) -> List[ToolDetection]:
        """
        Detect tools on a single page

        Args:
            url: Page URL
            html: Raw HTML
            markdown: Cleaned markdown/text

        Returns:
            List of ToolDetection objects
        """
        html_clean = self.clean_html(html)
        text_clean = self.clean_text(markdown)

        prompt = self.get_prompt(url, html_clean, text_clean)

        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a tool detection expert. Return valid JSON with evidence."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            result = json.loads(response.choices[0].message.content.strip())
            tools = result.get("tools", [])

            # Convert to ToolDetection objects
            detections = []
            for tool_data in tools:
                try:
                    detection = ToolDetection(**tool_data)
                    detections.append(detection)
                except Exception as e:
                    logger.warning(f"  Warning: Failed to parse tool {tool_data.get('tool_name')}: {e}")

            return detections

        except Exception as e:
            logger.error(f"  Error detecting tools: {str(e)[:80]}")
            # Return empty detections for all tools
            return [
                ToolDetection(
                    tool_name=tool.value,
                    isPresent=False,
                    confidence=0.0,
                    evidence="Detection failed",
                    location="unknown",
                    url=url,
                    notes=f"Error: {str(e)[:50]}"
                )
                for tool in ToolType
            ]

    async def detect_page_data(self, page_data: Dict[str, Any]) -> List[ToolDetection]:
        """
        Detect tools from page data (for parallel processing)

        Args:
            page_data: Dictionary with 'url', 'html', 'markdown' keys

        Returns:
            List of ToolDetection objects
        """
        return await self.detect(
            url=page_data['url'],
            html=page_data['html'],
            markdown=page_data['markdown']
        )

    async def detect_batch_parallel(self, pages_data: List[Dict[str, Any]]) -> List[List[ToolDetection]]:
        """
        Detect tools from multiple pages in parallel

        Args:
            pages_data: List of page data dictionaries with 'url', 'html', 'markdown' keys

        Returns:
            List of detection results (one per page)
        """
        if not self.enable_parallel or len(pages_data) <= 1:
            # Fall back to sequential processing
            results = []
            for page_data in pages_data:
                detections = await self.detect_page_data(page_data)
                results.append(detections)
            return results

        logger.info(f"  🚀 Using parallel tool detection with {self.max_workers} workers")

        all_results = []

        # Process pages in batches
        total_pages = len(pages_data)
        for batch_start in range(0, total_pages, self.max_workers):
            batch_end = min(batch_start + self.max_workers, total_pages)
            page_batch = pages_data[batch_start:batch_end]
            batch_num = (batch_start // self.max_workers) + 1

            logger.info(f"  📦 Processing batch {batch_num} ({len(page_batch)} pages)...")

            # Create tasks for this batch
            tasks = [self.detect_page_data(page_data) for page_data in page_batch]

            # Run all tasks concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"  ✗ Error in batch processing: {str(result)[:80]}")
                    # Return empty detections for failed pages
                    all_results.append([
                        ToolDetection(
                            tool_name=tool.value,
                            isPresent=False,
                            confidence=0.0,
                            evidence="Detection failed",
                            location="unknown",
                            url=page_batch[i]['url'],
                            notes=f"Error: {str(result)[:50]}"
                        )
                        for tool in ToolType
                    ])
                else:
                    all_results.append(result)

            # Small delay between batches
            if batch_end < total_pages:
                await asyncio.sleep(1.0)

        return all_results

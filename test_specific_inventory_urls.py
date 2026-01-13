#!/usr/bin/env python3
"""
Test inventory extraction from specific URLs
Extract vehicle data from VDP or SRP pages directly

Features:
- Enhanced content filtering (removes nav, footers, chat widgets, legal disclaimers)
- VIN enrichment using NHTSA API (fills missing fields automatically)
"""
import os
import asyncio
from dealership_scraper.extractors import InventoryExtractor


async def test_specific_inventory_urls():
    """Extract inventory from specific URLs"""
    API_KEY = os.getenv("OPENAI_API_KEY")

    if not API_KEY:
        print("❌ Error: OPENAI_API_KEY not set")
        return

    # ============================================
    # CUSTOMIZE THESE URLS
    # ============================================
    URLS_TO_TEST = [
        "https://www.cardinalewaymazdapeoria.com/inventory/used"
        # "https://www.cardinalenissan.com/viewdetails/new/3n8ap6da4sl372859/2025-nissan-kicks-sport-utility?type=cash"
        # "https://www.cardinalenissan.com/inventory/new/nissan/kicks?paymenttype=lease&instock=true&intransit=true&inproduction=true",
        # Add more inventory URLs here:
        # "https://www.cardinalenissan.com/new-inventory",
        # "https://www.cardinalenissan.com/used-inventory",
    ]
    # ============================================

    print("\n" + "="*80)
    print("SPECIFIC URL INVENTORY EXTRACTION")
    print("="*80)
    print(f"Testing {len(URLS_TO_TEST)} URL(s)")
    print("="*80 + "\n")

    # Initialize extractor with VIN enrichment enabled
    # VIN enrichment fills missing fields using NHTSA API (no extra tokens!)
    inventory_extractor = InventoryExtractor(
        API_KEY,
        enrich_with_vin=True     # Enable VIN enrichment
    )

    # Extract all vehicles at once - extractor handles crawling internally
    print(f"🚀 Extracting inventory with VIN enrichment...\n")
    all_vehicles = await inventory_extractor.extract(URLS_TO_TEST)

    # Save results
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"\n✓ Total vehicles extracted: {len(all_vehicles)}\n")

    if all_vehicles:
        import json
        os.makedirs("output", exist_ok=True)

        with open("output/inventory.json", "w", encoding="utf-8") as f:
            json.dump(all_vehicles, f, indent=2, ensure_ascii=False)

        print(f"✓ Saved: output/inventory.json")
        print(f"✓ Debug files: output/debug/")

        # Show detailed breakdown (first 10 vehicles)
        print("\n" + "="*80)
        print("VEHICLE BREAKDOWN (First 10)")
        print("="*80 + "\n")

        for i, vehicle in enumerate(all_vehicles[:10], 1):
            print(f"Vehicle {i}:")
            print(f"  Make/Model: {vehicle.get('make', 'N/A')} {vehicle.get('model', 'N/A')}")
            print(f"  Year: {vehicle.get('year', 'N/A')}")
            print(f"  Trim: {vehicle.get('trim', 'N/A')}")
            print(f"  VIN: {vehicle.get('vin', 'N/A')}")

            # Show pricing info
            price = vehicle.get('price')
            currency = vehicle.get('currency') or 'USD'
            monthly = vehicle.get('monthly_payment')

            if price:
                print(f"  Price: {currency} {price:,.2f}")
            else:
                print(f"  Price: N/A")

            if monthly:
                print(f"  Monthly Payment: {currency} {monthly:,.2f}/mo")

            print(f"  Stock #: {vehicle.get('stock_number', 'N/A')}")

            # Show enriched fields (from VIN)
            if vehicle.get('transmission'):
                print(f"  Transmission: {vehicle['transmission']}")
            if vehicle.get('fuel_type'):
                print(f"  Fuel Type: {vehicle['fuel_type']}")
            if vehicle.get('drivetrain'):
                print(f"  Drivetrain: {vehicle['drivetrain']}")
            if vehicle.get('engine'):
                print(f"  Engine: {vehicle['engine']}")
            if vehicle.get('safety_features'):
                print(f"  Safety Features: {', '.join(vehicle['safety_features'][:3])}...")

            print()

        if len(all_vehicles) > 10:
            print(f"... and {len(all_vehicles) - 10} more vehicles")

    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_specific_inventory_urls())

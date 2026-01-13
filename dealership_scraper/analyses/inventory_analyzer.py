#!/usr/bin/env python3
"""
Inventory Analyzer - Statistical analysis of dealership inventory data
Analyzes vehicle pricing by type and condition from inventory JSON files
"""
import json
import sys
import os
import math
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime


# ========== CONFIGURATION ==========

VEHICLE_TYPES = [
    "Sedan", "SUV", "Truck", "Coupe", "Convertible", "Hatchback",
    "Wagon", "Van", "Minivan", "Crossover", "Pickup", "Sports Car",
    "Luxury", "Compact"
]

CONDITION_MAPPING = {
    "New": ["New", "new", "NEW"],
    "Used": ["Used", "used", "USED", "Pre-Owned", "pre-owned", "PRE-OWNED"],
    "Certified": ["Certified", "certified", "CERTIFIED", "Certified Pre-Owned",
                  "CPO", "cpo", "Certified Pre Owned"]
}

# Values that should be treated as unknown/null
UNKNOWN_VALUES = [
    None, "", " ", "null", "NULL", "Null",
    "N/A", "n/a", "NA", "na",
    "Unknown", "unknown", "UNKNOWN",
    "Not specified", "not specified",
    "Not Specified", "NOT SPECIFIED",
    "-", "—", "–"
]


# ========== HELPER FUNCTIONS ==========

def is_unknown_value(value: Any) -> bool:
    """
    Check if value should be treated as unknown/null

    Args:
        value: Value to check

    Returns:
        True if value is unknown/null
    """
    # Check None
    if value is None:
        return True

    # Check NaN
    if isinstance(value, float) and math.isnan(value):
        return True

    # Check if in unknown list
    if value in UNKNOWN_VALUES:
        return True

    # Check empty string after strip
    if isinstance(value, str) and value.strip() == "":
        return True

    return False


def normalize_condition(condition: Any) -> str:
    """
    Normalize condition to standard categories

    Args:
        condition: Raw condition value from data

    Returns:
        One of: 'New', 'Used', 'Certified', 'Unknown'
    """
    # Check if unknown
    if is_unknown_value(condition):
        return "Unknown"

    # Check known conditions
    for standard, variants in CONDITION_MAPPING.items():
        if condition in variants:
            return standard

    # Anything else is unknown
    return "Unknown"


def normalize_vehicle_type(vehicle_type: Any) -> Tuple[str, str]:
    """
    Normalize vehicle type and categorize

    Args:
        vehicle_type: Raw vehicle_type value from data

    Returns:
        Tuple of (normalized_value, category)
        category: 'known', 'others', or 'unknown'
    """
    # Check if unknown
    if is_unknown_value(vehicle_type):
        return ("Unknown", "unknown")

    # Check if known type
    if vehicle_type in VEHICLE_TYPES:
        return (vehicle_type, "known")

    # Valid but not in predefined list = Others
    return (vehicle_type, "others")


def extract_price(price_value: Any) -> float:
    """
    Extract numeric price from various formats

    Args:
        price_value: Price value (could be float, int, string, or None)

    Returns:
        Float price or 0.0 if invalid
    """
    if price_value is None:
        return 0.0

    # Already a number
    if isinstance(price_value, (int, float)):
        # Check for NaN
        if isinstance(price_value, float) and math.isnan(price_value):
            return 0.0
        return float(price_value)

    # String format (e.g., "$28,500" or "28500")
    if isinstance(price_value, str):
        try:
            # Remove $, commas, and spaces
            cleaned = price_value.replace('$', '').replace(',', '').replace(' ', '').strip()
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0

    return 0.0


def calculate_mean_price(vehicles: List[Dict]) -> float:
    """
    Calculate mean price from list of vehicles

    Args:
        vehicles: List of vehicle dictionaries

    Returns:
        Mean price or 0.0 if no valid prices
    """
    valid_prices = []

    for vehicle in vehicles:
        price = extract_price(vehicle.get('price'))
        if price > 0:  # Only count positive prices
            valid_prices.append(price)

    if not valid_prices:
        return 0.0

    return sum(valid_prices) / len(valid_prices)


def group_by_vehicle_type(vehicles: List[Dict]) -> Dict[str, Dict[str, Any]]:
    """
    Group vehicles by normalized vehicle_type with categorization

    Args:
        vehicles: List of vehicle dictionaries

    Returns:
        Dictionary with structure:
        {
            'known': {'SUV': [vehicle1, ...], 'Sedan': [...]},
            'others': {'Electric SUV': [...], '4dr Car': [...]},
            'unknown': [vehicle1, ...]
        }
    """
    grouped = {
        'known': {},
        'others': {},
        'unknown': []
    }

    for vehicle in vehicles:
        raw_type = vehicle.get('vehicle_type')
        normalized_type, category = normalize_vehicle_type(raw_type)

        if category == 'known':
            if normalized_type not in grouped['known']:
                grouped['known'][normalized_type] = []
            grouped['known'][normalized_type].append(vehicle)

        elif category == 'others':
            if normalized_type not in grouped['others']:
                grouped['others'][normalized_type] = []
            grouped['others'][normalized_type].append(vehicle)

        else:  # unknown
            grouped['unknown'].append(vehicle)

    return grouped


def group_by_condition(vehicles: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group vehicles by normalized condition

    Args:
        vehicles: List of vehicle dictionaries

    Returns:
        Dictionary mapping condition to list of vehicles
    """
    grouped = {}

    for vehicle in vehicles:
        raw_condition = vehicle.get('condition')
        condition = normalize_condition(raw_condition)

        if condition not in grouped:
            grouped[condition] = []

        grouped[condition].append(vehicle)

    return grouped


# ========== ANALYSIS FUNCTIONS ==========

def analyze_overall_stats(vehicles: List[Dict]) -> Dict[str, Any]:
    """
    Calculate overall statistics for all vehicles

    Args:
        vehicles: List of vehicle dictionaries

    Returns:
        Dictionary with overall statistics
    """
    total_vehicles = len(vehicles)

    # Count vehicles with valid prices
    vehicles_with_price = [v for v in vehicles if extract_price(v.get('price')) > 0]

    # Calculate average
    average_price = calculate_mean_price(vehicles)

    return {
        "total_vehicles": total_vehicles,
        "vehicles_with_valid_price": len(vehicles_with_price),
        "average_price": round(average_price, 2)
    }


def analyze_vehicle_type_stats(vehicles: List[Dict]) -> Dict[str, Any]:
    """
    Calculate statistics by vehicle type with Known/Others/Unknown categorization

    Args:
        vehicles: List of vehicle dictionaries

    Returns:
        Dictionary with vehicle type statistics
    """
    grouped = group_by_vehicle_type(vehicles)
    stats = {}

    # Process known types
    for vehicle_type, type_vehicles in grouped['known'].items():
        mean_price = calculate_mean_price(type_vehicles)
        stats[vehicle_type] = {
            "count": len(type_vehicles),
            "mean_price": round(mean_price, 2),
            "category": "known"
        }

    # Process Others (with breakdown)
    if grouped['others']:
        others_all_vehicles = []
        breakdown = {}

        for vehicle_type, type_vehicles in grouped['others'].items():
            mean_price = calculate_mean_price(type_vehicles)
            breakdown[vehicle_type] = {
                "count": len(type_vehicles),
                "mean_price": round(mean_price, 2)
            }
            others_all_vehicles.extend(type_vehicles)

        stats["Others"] = {
            "total_count": len(others_all_vehicles),
            "overall_mean": round(calculate_mean_price(others_all_vehicles), 2),
            "category": "others",
            "breakdown": breakdown
        }

    # Process Unknown
    if grouped['unknown']:
        mean_price = calculate_mean_price(grouped['unknown'])
        stats["Unknown"] = {
            "count": len(grouped['unknown']),
            "mean_price": round(mean_price, 2),
            "category": "unknown"
        }

    return stats


def analyze_condition_stats(vehicles: List[Dict]) -> Dict[str, Any]:
    """
    Calculate statistics by condition with nested vehicle_type breakdown

    Args:
        vehicles: List of vehicle dictionaries

    Returns:
        Dictionary mapping condition to its statistics
    """
    condition_groups = group_by_condition(vehicles)
    stats = {}

    for condition, condition_vehicles in condition_groups.items():
        # Overall stats for this condition
        overall_mean = calculate_mean_price(condition_vehicles)

        # Vehicle type breakdown within this condition
        type_grouped = group_by_vehicle_type(condition_vehicles)
        vehicle_type_means = {}

        # Known types
        for vehicle_type, type_vehicles in type_grouped['known'].items():
            mean_price = calculate_mean_price(type_vehicles)
            vehicle_type_means[vehicle_type] = {
                "count": len(type_vehicles),
                "mean_price": round(mean_price, 2),
                "category": "known"
            }

        # Others (with breakdown)
        if type_grouped['others']:
            others_all = []
            breakdown = {}

            for vehicle_type, type_vehicles in type_grouped['others'].items():
                mean_price = calculate_mean_price(type_vehicles)
                breakdown[vehicle_type] = {
                    "count": len(type_vehicles),
                    "mean_price": round(mean_price, 2)
                }
                others_all.extend(type_vehicles)

            vehicle_type_means["Others"] = {
                "total_count": len(others_all),
                "overall_mean": round(calculate_mean_price(others_all), 2),
                "category": "others",
                "breakdown": breakdown
            }

        # Unknown
        if type_grouped['unknown']:
            mean_price = calculate_mean_price(type_grouped['unknown'])
            vehicle_type_means["Unknown"] = {
                "count": len(type_grouped['unknown']),
                "mean_price": round(mean_price, 2),
                "category": "unknown"
            }

        stats[condition] = {
            "count": len(condition_vehicles),
            "overall_mean": round(overall_mean, 2),
            "category": "known" if condition in ["New", "Used", "Certified"] else "unknown",
            "vehicle_type_means": vehicle_type_means
        }

    return stats


def analyze_inventory(inventory_data: List[Dict], domain: str) -> Dict[str, Any]:
    """
    Perform complete analysis on inventory

    Args:
        inventory_data: List of vehicle dictionaries
        domain: Domain name for identification

    Returns:
        Complete analysis results
    """
    print(f"\n{'='*80}")
    print(f"ANALYZING INVENTORY: {domain}")
    print(f"{'='*80}\n")

    # Perform analyses
    overall = analyze_overall_stats(inventory_data)
    vehicle_types = analyze_vehicle_type_stats(inventory_data)
    conditions = analyze_condition_stats(inventory_data)

    return {
        "overall_stats": overall,
        "vehicle_type_stats": vehicle_types,
        "condition_stats": conditions
    }


# ========== INPUT VALIDATION ==========

def extract_file_prefix(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract prefix and type from filename

    Args:
        file_path: Path to file

    Returns:
        Tuple of (prefix, file_type) or (None, None) if invalid

    Examples:
        'dealer1_inventory.json' → ('dealer1', 'inventory')
        '/path/to/dealer1_tools.json' → ('dealer1', 'tools')
        '_inventory.json' → ('', 'inventory')
    """
    filename = os.path.basename(file_path)

    # Check for _inventory.json
    if filename.endswith('_inventory.json'):
        prefix = filename[:-len('_inventory.json')]
        return (prefix, 'inventory')

    # Check for _tools.json
    elif filename.endswith('_tools.json'):
        prefix = filename[:-len('_tools.json')]
        return (prefix, 'tools')

    return (None, None)


def validate_and_pair_files(file_paths: List[str]) -> Dict[str, Dict[str, str]]:
    """
    Validate input files and pair inventory with tools

    Args:
        file_paths: List of JSON file paths

    Returns:
        Dictionary mapping prefix to file pairs

    Raises:
        ValueError: If files not properly paired or invalid
    """
    files_by_prefix = {}

    # Group files by prefix
    for path in file_paths:
        prefix, file_type = extract_file_prefix(path)

        if prefix is None:
            raise ValueError(f"Invalid file: {path}\nMust end with '_inventory.json' or '_tools.json'")

        # Initialize group if first time seeing this prefix
        if prefix not in files_by_prefix:
            files_by_prefix[prefix] = {}

        # Check for duplicates
        if file_type in files_by_prefix[prefix]:
            raise ValueError(f"Duplicate {file_type} file for prefix '{prefix}'")

        # Store file path
        files_by_prefix[prefix][file_type] = path

    # Validate each prefix has both inventory and tools
    paired = {}
    for prefix, files in files_by_prefix.items():
        if 'inventory' not in files:
            raise ValueError(f"Missing inventory file for prefix '{prefix}'\nFound tools: {files.get('tools')}")
        if 'tools' not in files:
            raise ValueError(f"Missing tools file for prefix '{prefix}'\nFound inventory: {files.get('inventory')}")

        paired[prefix] = {
            'inventory': files['inventory'],
            'tools': files['tools']
        }

    # Check minimum requirement
    if len(paired) < 1:
        raise ValueError("Need at least 1 domain (2 files: inventory + tools)")

    return paired


def load_json_file(file_path: str) -> Any:
    """
    Load JSON file with error handling

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {str(e)}")


def save_calculations_json(calculations: Dict[str, Any], output_path: str):
    """
    Save calculations to JSON file

    Args:
        calculations: Analysis results dictionary
        output_path: Path to save JSON file
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(calculations, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved calculations: {output_path}")
    except Exception as e:
        print(f"❌ Error saving calculations: {str(e)}")


# ========== DISPLAY FUNCTIONS ==========

def print_overall_stats(stats: Dict[str, Any]):
    """Print overall statistics"""
    print("📊 OVERALL STATISTICS:")
    print(f"  Total Vehicles:            {stats['total_vehicles']}")
    print(f"  Vehicles with Valid Price: {stats['vehicles_with_valid_price']}")
    print(f"  Average Price:             ${stats['average_price']:,.2f}")


def print_vehicle_type_stats(stats: Dict[str, Any]):
    """Print vehicle type statistics with Known/Others/Unknown"""
    print("\n🚗 VEHICLE TYPE STATISTICS:")

    # Separate by category
    known_types = {k: v for k, v in stats.items() if v.get('category') == 'known'}
    others = stats.get('Others')
    unknown = stats.get('Unknown')

    # Print known types (sorted by count)
    if known_types:
        print("\n  Known Types:")
        sorted_types = sorted(known_types.items(), key=lambda x: x[1]['count'], reverse=True)
        for vehicle_type, type_stats in sorted_types:
            print(f"    {vehicle_type:20s} {type_stats['count']:4d} vehicles  ${type_stats['mean_price']:,.2f}")

    # Print Others with breakdown
    if others:
        print(f"\n  Others ({others['total_count']} vehicles, avg ${others['overall_mean']:,.2f}):")
        sorted_others = sorted(others['breakdown'].items(), key=lambda x: x[1]['count'], reverse=True)
        for vehicle_type, type_stats in sorted_others:
            print(f"    {vehicle_type:20s} {type_stats['count']:4d} vehicles  ${type_stats['mean_price']:,.2f}")

    # Print Unknown
    if unknown:
        print(f"\n  Unknown:")
        print(f"    {unknown['count']} vehicles  ${unknown['mean_price']:,.2f}")


def print_condition_stats(stats: Dict[str, Any]):
    """Print condition statistics with nested vehicle types"""
    print("\n🏷️  CONDITION STATISTICS:")

    # Sort conditions: Known first (New, Used, Certified), then Unknown
    known_conditions = {k: v for k, v in stats.items() if k in ["New", "Used", "Certified"]}
    unknown_condition = stats.get("Unknown")

    for condition, cond_stats in known_conditions.items():
        print(f"\n  {condition} ({cond_stats['count']} vehicles):")
        print(f"    Overall Mean: ${cond_stats['overall_mean']:,.2f}")
        print(f"    Vehicle Type Breakdown:")

        type_means = cond_stats['vehicle_type_means']

        # Known types
        known = {k: v for k, v in type_means.items() if v.get('category') == 'known'}
        if known:
            print(f"      Known Types:")
            sorted_known = sorted(known.items(), key=lambda x: x[1]['count'], reverse=True)
            for vtype, vstats in sorted_known:
                print(f"        {vtype:18s} ({vstats['count']:3d} vehicles)  ${vstats['mean_price']:,.2f}")

        # Others
        others = type_means.get('Others')
        if others:
            print(f"      Others ({others['total_count']} vehicles, avg ${others['overall_mean']:,.2f}):")
            sorted_others = sorted(others['breakdown'].items(), key=lambda x: x[1]['count'], reverse=True)
            for vtype, vstats in sorted_others:
                print(f"        {vtype:18s} ({vstats['count']:3d} vehicles)  ${vstats['mean_price']:,.2f}")

        # Unknown
        unknown_type = type_means.get('Unknown')
        if unknown_type:
            print(f"      Unknown:")
            print(f"        {unknown_type['count']} vehicles  ${unknown_type['mean_price']:,.2f}")

    # Unknown condition
    if unknown_condition:
        print(f"\n  Unknown Condition ({unknown_condition['count']} vehicles):")
        print(f"    Overall Mean: ${unknown_condition['overall_mean']:,.2f}")
        # Could add breakdown here if needed


def print_analysis(analysis: Dict[str, Any]):
    """Print complete analysis results"""
    print_overall_stats(analysis['overall_stats'])
    print_vehicle_type_stats(analysis['vehicle_type_stats'])
    print_condition_stats(analysis['condition_stats'])
    print(f"\n{'='*80}\n")


# ========== MAIN EXECUTION ==========

def main():
    """Main entry point"""

    # Check command line arguments
    if len(sys.argv) < 3:
        print("❌ Error: Insufficient arguments")
        print("\nUsage:")
        print("  python inventory_analyzer.py <file1_inventory.json> <file1_tools.json> [file2_inventory.json file2_tools.json ...]")
        print("\nExample:")
        print("  python inventory_analyzer.py \\")
        print("    dealer1_inventory.json dealer1_tools.json \\")
        print("    dealer2_inventory.json dealer2_tools.json")
        print("\nNote:")
        print("  - Files must end with '_inventory.json' or '_tools.json'")
        print("  - Files must come in pairs (matching prefix)")
        print("  - Prefix can be anything: dealer1, www.example.com, my-dealer-123, etc.")
        sys.exit(1)

    # Get file paths (skip script name)
    file_paths = sys.argv[1:]

    # Check even number of files (must be in pairs)
    if len(file_paths) % 2 != 0:
        print(f"❌ Error: Odd number of files ({len(file_paths)})")
        print("   Files must come in pairs: *_inventory.json + *_tools.json")
        sys.exit(1)

    try:
        # Validate and pair files
        print(f"📥 Loading {len(file_paths)} files ({len(file_paths)//2} domains)...")
        paired_files = validate_and_pair_files(file_paths)
        print(f"✓ Validated {len(paired_files)} domain(s)\n")

        # Process each domain
        successful = 0
        failed = 0

        for prefix, files in paired_files.items():
            try:
                # Load inventory
                inventory_data = load_json_file(files['inventory'])

                # Verify it's a list
                if not isinstance(inventory_data, list):
                    print(f"⚠️  Warning: {prefix} - Expected list of vehicles, got {type(inventory_data)}")
                    failed += 1
                    continue

                # Analyze inventory
                analysis = analyze_inventory(inventory_data, prefix if prefix else "(empty prefix)")

                # Print results
                print_analysis(analysis)

                # Create calculations JSON
                calculations = {
                    "metadata": {
                        "domain": prefix if prefix else "(empty prefix)",
                        "source_file": files['inventory'],
                        "total_vehicles": len(inventory_data),
                        "analysis_timestamp": datetime.now().isoformat()
                    },
                    "statistics": analysis
                }

                # Save calculations to file
                output_filename = f"{prefix}_inventory_calculations.json" if prefix else "_inventory_calculations.json"
                save_calculations_json(calculations, output_filename)

                successful += 1
                print(f"✅ SUCCESS: {prefix if prefix else '(empty prefix)'}\n")

            except Exception as e:
                failed += 1
                print(f"❌ Error processing {prefix if prefix else '(empty prefix)'}: {str(e)}\n")
                continue

        # Final summary
        print(f"{'='*80}")
        print(f"ANALYSIS COMPLETE")
        print(f"{'='*80}")
        print(f"✅ Successfully analyzed: {successful}/{len(paired_files)} domains")

        if failed > 0:
            print(f"❌ Failed: {failed} domain(s)")

        print(f"{'='*80}\n")

    except ValueError as e:
        print(f"❌ Validation Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

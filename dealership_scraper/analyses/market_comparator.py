#!/usr/bin/env python3
"""
Market Comparator - Dealership Competitive Analysis Tool

Compares user dealership inventory and tools against competitor market data.
Uses GPT-4o-mini for intelligent market analysis and sales insights.

Usage:
    python market_comparator.py \
        user_{prefix}_inventory.json \
        user_{prefix}_tools.json \
        competitor1_inventory.json \
        competitor1_tools.json \
        [more competitor pairs...]
"""

import json
import os
import sys
import math
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Import functions from inventory_analyzer 
from inventory_analyzer import (
    is_unknown_value,
    extract_price,
    calculate_mean_price,
    normalize_vehicle_type,
    normalize_condition,
    group_by_vehicle_type,
    group_by_condition,
    analyze_vehicle_type_stats,
    analyze_condition_stats,
    analyze_inventory
)


# ============================================================================
# FILE VALIDATION AND SEPARATION
# ============================================================================

def extract_file_info(file_path: str) -> Optional[Dict[str, str]]:
    """
    Extract information from filename.

    Returns:
        {
            'full_path': 'path/to/file.json',
            'filename': 'user_dealer1_inventory.json',
            'prefix': 'user_dealer1',
            'type': 'inventory' or 'tools',
            'is_user': True/False
        }
    """
    filename = os.path.basename(file_path)

    # Check for inventory file
    if filename.endswith('_inventory.json'):
        prefix = filename[:-len('_inventory.json')]
        return {
            'full_path': file_path,
            'filename': filename,
            'prefix': prefix,
            'type': 'inventory',
            # Support both "user_" and "client_" prefixes as user files
            'is_user': prefix.startswith('user_') or prefix.startswith('client_')
        }

    # Check for tools file
    elif filename.endswith('_tools.json'):
        prefix = filename[:-len('_tools.json')]
        return {
            'full_path': file_path,
            'filename': filename,
            'prefix': prefix,
            'type': 'tools',
            # Support both "user_" and "client_" prefixes as user files
            'is_user': prefix.startswith('user_') or prefix.startswith('client_')
        }

    return None


def validate_and_separate_files(file_paths: List[str]) -> Dict[str, Any]:
    """
    Validates input files and separates user from competitors.

    Returns:
        {
            'user': {
                'prefix': 'user_dealer1',
                'inventory': '/path/to/user_dealer1_inventory.json',
                'tools': '/path/to/user_dealer1_tools.json'
            },
            'competitors': [
                {
                    'prefix': 'competitor1',
                    'name': 'competitor1',
                    'inventory': '/path/to/competitor1_inventory.json',
                    'tools': '/path/to/competitor1_tools.json'
                },
                ...
            ]
        }
    """
    files_by_prefix = {}

    # Group files by prefix
    for path in file_paths:
        info = extract_file_info(path)
        if info is None:
            print(f"⚠️  Skipping invalid file: {path}")
            continue

        prefix = info['prefix']
        if prefix not in files_by_prefix:
            files_by_prefix[prefix] = {'is_user': info['is_user']}

        files_by_prefix[prefix][info['type']] = info['full_path']

    # Separate user and competitors
    user_data = None
    competitors = []

    for prefix, files in files_by_prefix.items():
        # Validate pairing
        if 'inventory' not in files:
            print(f"⚠️  Skipping prefix '{prefix}': Missing inventory file")
            continue
        if 'tools' not in files:
            print(f"⚠️  Skipping prefix '{prefix}': Missing tools file")
            continue

        entry = {
            'prefix': prefix,
            'inventory': files['inventory'],
            'tools': files['tools']
        }

        if files['is_user']:
            if user_data is not None:
                raise ValueError(f"Multiple user_ prefixes found: {user_data['prefix']} and {prefix}")
            user_data = entry
        else:
            entry['name'] = prefix
            competitors.append(entry)

    # Validation
    if user_data is None:
        raise ValueError("No user_ prefixed files found. User files must start with 'user_'")

    if len(competitors) == 0:
        raise ValueError("No competitor files found. Need at least 1 competitor for comparison")

    return {
        'user': user_data,
        'competitors': competitors
    }


# ============================================================================
# CALCULATIONS GENERATION
# ============================================================================

def load_json_file(file_path: str) -> Any:
    """Load and parse JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {str(e)}")


def generate_calculations_for_inventory(inventory_path: str, prefix: str) -> Dict[str, Any]:
    """
    Generate inventory calculations using inventory_analyzer functions.
    Saves to {prefix}_inventory_calculations.json

    Returns: calculations dict
    """
    print(f"  📊 Analyzing inventory: {prefix}")

    # Load inventory
    inventory_data = load_json_file(inventory_path)

    if not isinstance(inventory_data, list):
        raise ValueError(f"Expected list of vehicles, got {type(inventory_data)}")

    # Generate analysis
    analysis = analyze_inventory(inventory_data, prefix)

    # Create calculations object
    calculations = {
        "metadata": {
            "domain": prefix,
            "source_file": inventory_path,
            "total_vehicles": len(inventory_data),
            "analysis_timestamp": datetime.now().isoformat()
        },
        "statistics": analysis
    }

    # Save to file
    output_file = f"{prefix}_inventory_calculations.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(calculations, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Saved: {output_file}")

    return calculations


def generate_all_calculations(files_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate calculations for user and all competitors.

    Returns:
        {
            'user': {
                'prefix': 'user_dealer1',
                'calculations': {...},
                'tools': {...}
            },
            'competitors': [
                {
                    'prefix': 'competitor1',
                    'name': 'competitor1',
                    'calculations': {...},
                    'tools': {...}
                },
                ...
            ]
        }
    """
    print("\n" + "="*80)
    print("GENERATING INVENTORY CALCULATIONS")
    print("="*80)

    # Process user
    print(f"\n🔵 User Dealership:")
    user_calculations = generate_calculations_for_inventory(
        files_dict['user']['inventory'],
        files_dict['user']['prefix']
    )
    user_tools = load_json_file(files_dict['user']['tools'])

    user_data = {
        'prefix': files_dict['user']['prefix'],
        'calculations': user_calculations,
        'tools': user_tools
    }

    # Process competitors
    print(f"\n🔴 Competitor Dealerships:")
    competitors_data = []

    for comp in files_dict['competitors']:
        comp_calculations = generate_calculations_for_inventory(
            comp['inventory'],
            comp['prefix']
        )
        comp_tools = load_json_file(comp['tools'])

        competitors_data.append({
            'prefix': comp['prefix'],
            'name': comp['name'],
            'calculations': comp_calculations,
            'tools': comp_tools
        })

    print(f"\n✓ Generated calculations for {1 + len(competitors_data)} dealerships")

    return {
        'user': user_data,
        'competitors': competitors_data
    }


# ============================================================================
# MARKET AGGREGATION
# ============================================================================

def extract_tools_list(tools_data: List[Dict]) -> List[str]:
    """Extract list of present tool names from tools JSON."""
    present_tools = []
    for tool in tools_data:
        # Support both formats for backward compatibility
        is_present = tool.get('is_present', tool.get('isPresent', False))
        if is_present:
            present_tools.append(tool.get('tool_name', 'Unknown'))
    return present_tools


def aggregate_market_statistics(competitors_data: List[Dict]) -> Dict[str, Any]:
    """
    Aggregate statistics across all competitors.
    Simple averages for all metrics.

    Returns:
        {
            'total_competitors': 5,
            'total_vehicles': 2035,
            'avg_vehicles_per_competitor': 407,
            'overall_avg_price': 35200.50,
            'price_range': {'min': 28000, 'max': 42000},
            'vehicle_types': {...},
            'conditions': {...},
            'tools': {...}
        }
    """
    if not competitors_data:
        return {}

    total_competitors = len(competitors_data)

    # Collect all prices and counts
    all_prices = []
    all_vehicle_counts = []
    vehicle_type_data = {}
    condition_data = {}
    tool_counts = {}

    for comp in competitors_data:
        stats = comp['calculations']['statistics']
        metadata = comp['calculations']['metadata']

        # Overall stats
        all_vehicle_counts.append(metadata['total_vehicles'])
        if 'overall_stats' in stats and 'average_price' in stats['overall_stats']:
            all_prices.append(stats['overall_stats']['average_price'])

        # Vehicle type stats
        if 'vehicle_type_stats' in stats:
            for vtype, vdata in stats['vehicle_type_stats'].items():
                if vtype not in vehicle_type_data:
                    vehicle_type_data[vtype] = []

                if isinstance(vdata, dict):
                    if 'mean_price' in vdata:
                        vehicle_type_data[vtype].append(vdata['mean_price'])
                    elif 'overall_mean' in vdata:  # For Others category
                        vehicle_type_data[vtype].append(vdata['overall_mean'])

        # Condition stats
        if 'condition_stats' in stats:
            for cond, cdata in stats['condition_stats'].items():
                if cond not in condition_data:
                    condition_data[cond] = []
                if 'overall_mean' in cdata:
                    condition_data[cond].append(cdata['overall_mean'])

        # Tools
        tools_list = extract_tools_list(comp['tools'])
        for tool in tools_list:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

    # Calculate market aggregates
    market_stats = {
        'total_competitors': total_competitors,
        'total_vehicles': sum(all_vehicle_counts),
        'avg_vehicles_per_competitor': sum(all_vehicle_counts) / total_competitors if all_vehicle_counts else 0,
        'overall_avg_price': sum(all_prices) / len(all_prices) if all_prices else 0,
        'price_range': {
            'min': min(all_prices) if all_prices else 0,
            'max': max(all_prices) if all_prices else 0
        },
        'vehicle_types': {},
        'conditions': {},
        'tools': {}
    }

    # Aggregate vehicle types
    for vtype, prices in vehicle_type_data.items():
        market_stats['vehicle_types'][vtype] = {
            'avg_price': sum(prices) / len(prices) if prices else 0,
            'present_in_n_competitors': len(prices)
        }

    # Aggregate conditions
    for cond, prices in condition_data.items():
        market_stats['conditions'][cond] = {
            'avg_price': sum(prices) / len(prices) if prices else 0,
            'present_in_n_competitors': len(prices)
        }

    # Tool prevalence
    for tool, count in tool_counts.items():
        market_stats['tools'][tool] = {
            'count': count,
            'prevalence': (count / total_competitors) * 100  # Percentage
        }

    return market_stats


def prepare_market_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare comprehensive market data for GPT analysis.

    Returns:
        {
            'user': {...},
            'market': {...},
            'competitor_details': [...]
        }
    """
    user_stats = data['user']['calculations']['statistics']
    user_metadata = data['user']['calculations']['metadata']
    user_tools = extract_tools_list(data['user']['tools'])

    # Extract user data
    user_summary = {
        'prefix': data['user']['prefix'],
        'total_vehicles': user_metadata['total_vehicles'],
        'overall_avg_price': user_stats.get('overall_stats', {}).get('average_price', 0),
        'vehicles_with_valid_price': user_stats.get('overall_stats', {}).get('vehicles_with_valid_price', 0),
        'vehicle_types': user_stats.get('vehicle_type_stats', {}),
        'conditions': user_stats.get('condition_stats', {}),
        'tools': user_tools,
        'tools_count': len(user_tools)
    }

    # Aggregate market data
    market_stats = aggregate_market_statistics(data['competitors'])

    # Extract competitor details
    competitor_details = []
    for comp in data['competitors']:
        comp_stats = comp['calculations']['statistics']
        comp_metadata = comp['calculations']['metadata']
        comp_tools = extract_tools_list(comp['tools'])

        competitor_details.append({
            'name': comp['name'],
            'total_vehicles': comp_metadata['total_vehicles'],
            'overall_avg_price': comp_stats.get('overall_stats', {}).get('average_price', 0),
            'tools': comp_tools,
            'tools_count': len(comp_tools)
        })

    return {
        'user': user_summary,
        'market': market_stats,
        'competitor_details': competitor_details
    }


# ============================================================================
# GPT PROMPT CONSTRUCTION
# ============================================================================

def build_comparison_prompt(market_data: Dict[str, Any]) -> str:
    """
    Build simple, condition-focused GPT prompt for market comparison.
    Focus on Used/New/Certified vehicle comparison with 7 bullets + conclusion.
    """
    user = market_data['user']
    market = market_data['market']
    competitors = market_data['competitor_details']

    prompt = f"""You are a dealership sales analyst. Compare the user's dealership against competitors, focusing primarily on Used, New, and Certified vehicle performance.

**USER DEALERSHIP:**
- Name: {user['prefix']}
- Total Vehicles: {user['total_vehicles']}
- Average Price: ${user['overall_avg_price']:,.2f}

**Condition Breakdown (User):**
{json.dumps(user['conditions'], indent=2)}

---

**MARKET (Aggregated from {market['total_competitors']} Competitors):**
- Total Market Vehicles: {market['total_vehicles']}
- Market Average Price: ${market['overall_avg_price']:,.2f}

**Market Conditions (Average Prices):**
{json.dumps(market['conditions'], indent=2)}

---

**ANALYSIS REQUIREMENTS:**

Provide a simple, clear comparison focusing on Used, New, and Certified vehicles.

**OUTPUT FORMAT (JSON):**

Return ONLY a valid JSON object with this exact structure:

{{
    "comparison_bullets": [
        "Bullet 1: Compare NEW vehicles (your avg price vs market, vehicle count, advantage/disadvantage)",
        "Bullet 2: Compare USED vehicles (your avg price vs market, vehicle count, advantage/disadvantage)",
        "Bullet 3: Compare CERTIFIED vehicles (your avg price vs market, vehicle count, advantage/disadvantage)",
        "Bullet 4: Overall pricing position (higher/lower than market and why)",
        "Bullet 5: Inventory size comparison (more/less vehicles than market average)",
        "Bullet 6: Which condition category is your strongest competitive advantage",
        "Bullet 7: Which condition category needs most improvement"
    ],
    "conclusion": "2-3 sentence summary: Overall competitive position, main strength, and primary recommendation for improvement."
}}

**INSTRUCTIONS:**
- Keep bullets short and specific (1-2 sentences each)
- Focus on NEW, USED, and CERTIFIED comparisons
- Use actual numbers and percentages
- Be direct and actionable
- Identify clear advantages and disadvantages
"""

    return prompt


# ============================================================================
# OPENAI API CALL
# ============================================================================

def call_gpt_analysis(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call GPT-4o-mini for market analysis.
    Includes retry logic and error handling.
    """
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment.\n"
            "Please set it in .env file or environment variable."
        )

    print("\n" + "="*80)
    print("CALLING GPT-4O-MINI FOR MARKET ANALYSIS")
    print("="*80)
    print("🤖 Analyzing competitive position...")

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )

    prompt = build_comparison_prompt(market_data)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert automotive dealership sales analyst specializing in competitive analysis and market insights. Provide detailed, actionable insights in valid JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            analysis = json.loads(response.choices[0].message.content)
            print("✓ Analysis complete")
            return analysis

        except json.JSONDecodeError as e:
            print(f"⚠️  Attempt {attempt + 1}/{max_retries}: Invalid JSON response")
            if attempt == max_retries - 1:
                raise ValueError(f"GPT returned invalid JSON after {max_retries} attempts: {str(e)}")

        except Exception as e:
            print(f"⚠️  Attempt {attempt + 1}/{max_retries}: API error: {str(e)}")
            if attempt == max_retries - 1:
                raise

    raise Exception("Failed to get valid analysis from GPT")


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def format_bullet_list(items: List[str], indent: int = 2) -> str:
    """Format list as bullet points with indentation."""
    indent_str = " " * indent
    return "\n".join([f"{indent_str}• {item}" for item in items])


def format_comparison_report(analysis: Dict[str, Any], market_data: Dict[str, Any]) -> str:
    """
    Format GPT analysis into simple, focused email report.
    """
    user = market_data['user']
    market = market_data['market']

    # Format bullets with numbering
    bullets_text = ""
    for i, bullet in enumerate(analysis['comparison_bullets'], 1):
        bullets_text += f"  {i}. {bullet}\n\n"

    # Calculate position metrics (handle division by zero)
    if market['avg_vehicles_per_competitor'] > 0:
        inv_diff = ((user['total_vehicles'] / market['avg_vehicles_per_competitor']) - 1) * 100
        inv_position = 'Above' if user['total_vehicles'] > market['avg_vehicles_per_competitor'] else 'Below'
        inv_text = f"{inv_position} market average ({inv_diff:+.1f}%)"
    else:
        inv_text = "N/A - no market data"

    if market['overall_avg_price'] > 0:
        price_diff = ((user['overall_avg_price'] / market['overall_avg_price']) - 1) * 100
        price_position = 'Above' if user['overall_avg_price'] > market['overall_avg_price'] else 'Below'
        price_text = f"{price_position} market average ({price_diff:+.1f}%)"
    else:
        price_text = "N/A - no market data"

    # Build simple report
    report = f"""
================================================================================
DEALERSHIP MARKET COMPARISON REPORT
================================================================================

USER DEALERSHIP: {user['prefix']}
COMPETITORS ANALYZED: {market['total_competitors']}
REPORT DATE: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

================================================================================

📊 KEY METRICS

YOUR DEALERSHIP:
  • Total Vehicles: {user['total_vehicles']}
  • Average Price: ${user['overall_avg_price']:,.2f}

MARKET AVERAGE:
  • Average Inventory: {market['avg_vehicles_per_competitor']:.0f} vehicles per competitor
  • Average Price: ${market['overall_avg_price']:,.2f}

YOUR POSITION:
  • Inventory Size: {inv_text}
  • Pricing: {price_text}

================================================================================
🔍 COMPETITIVE ANALYSIS (Used / New / Certified Focus)
================================================================================

{bullets_text}
================================================================================
💡 CONCLUSION
================================================================================

{analysis['conclusion']}

================================================================================

Report generated using AI-powered market analysis (GPT-4o-mini).

================================================================================
"""

    return report


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """
    Entry point for market comparator.

    Usage:
        # Option 1: Files in inputs/ directory (automatic)
        python market_comparator.py

        # Option 2: Specify files explicitly
        python market_comparator.py \
            user_dealer1_inventory.json \
            user_dealer1_tools.json \
            competitor1_inventory.json \
            competitor1_tools.json
    """
    print("\n" + "="*80)
    print("DEALERSHIP MARKET COMPARATOR")
    print("="*80)

    try:
        # Check if files provided via command line or use inputs/ directory
        if len(sys.argv) > 1:
            # Files provided via command line
            file_paths = sys.argv[1:]
            print("\n📂 Using files from command line arguments")
        else:
            # Look for inputs/ directory
            inputs_dir = "inputs"
            if not os.path.exists(inputs_dir):
                print(f"\n❌ Error: No files provided and '{inputs_dir}/' directory not found")
                print("\nUsage:")
                print("  Option 1: Create 'inputs/' directory and place JSON files there")
                print("  Option 2: Provide files as arguments:")
                print("    python market_comparator.py \\")
                print("        user_{prefix}_inventory.json \\")
                print("        user_{prefix}_tools.json \\")
                print("        competitor1_inventory.json \\")
                print("        competitor1_tools.json \\")
                print("        [more competitor pairs...]")
                print("\nNote: User files must start with 'user_' prefix")
                print("      Minimum: 1 user pair + 1 competitor pair")
                sys.exit(1)

            # Get all JSON files from inputs/ directory
            file_paths = []
            for filename in os.listdir(inputs_dir):
                if filename.endswith('.json'):
                    file_paths.append(os.path.join(inputs_dir, filename))

            if len(file_paths) < 4:
                print(f"\n❌ Error: Not enough JSON files in '{inputs_dir}/' directory")
                print(f"Found {len(file_paths)} files, need at least 4 (2 user + 2 competitor)")
                sys.exit(1)

            print(f"\n📂 Using {len(file_paths)} files from '{inputs_dir}/' directory")

        # Phase 1: Validate and separate files
        print("\n📂 Validating input files...")
        files_dict = validate_and_separate_files(file_paths)
        print(f"✓ Found user dealership: {files_dict['user']['prefix']}")
        print(f"✓ Found {len(files_dict['competitors'])} competitors")

        # Phase 2: Generate calculations
        data = generate_all_calculations(files_dict)

        # Phase 3: Prepare market summary
        print("\n" + "="*80)
        print("PREPARING MARKET SUMMARY")
        print("="*80)
        market_data = prepare_market_summary(data)
        print(f"✓ Market summary prepared")
        print(f"  - User: {market_data['user']['total_vehicles']} vehicles, ${market_data['user']['overall_avg_price']:,.2f} avg")
        print(f"  - Market: {market_data['market']['total_vehicles']} total vehicles across {market_data['market']['total_competitors']} competitors")

        # Phase 4 & 5: Call GPT for analysis
        analysis = call_gpt_analysis(market_data)

        # Phase 6: Format and save report
        print("\n" + "="*80)
        print("GENERATING FINAL REPORT")
        print("="*80)

        report = format_comparison_report(analysis, market_data)

        # Save to email.txt
        output_file = "email.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"✓ Report saved to: {output_file}")

        # Also display on terminal
        print("\n" + "="*80)
        print("REPORT PREVIEW")
        print("="*80)
        print(report)

        print("\n" + "="*80)
        print("✅ MARKET COMPARISON COMPLETE")
        print("="*80)
        print(f"📧 Full report saved to: {output_file}")
        print("="*80)

    except ValueError as e:
        print(f"\n❌ Validation Error: {str(e)}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ File Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

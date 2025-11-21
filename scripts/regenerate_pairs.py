#!/usr/bin/env python3
"""
Utility script to regenerate makerbot_command_params.json from bot_settings.json

This script reads your bot_settings.json and regenerates the trading pair
configurations, applying the limit_to_coins filter if set.

Usage:
    python3 scripts/regenerate_pairs.py

The script will:
1. Read settings from config/bot_settings.json
2. Apply the limit_to_coins filter (if set)
3. Preserve custom settings for pairs that match the filter
4. Write the new configuration to config/makerbot_command_params.json
"""
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Config

def main():
    print("=" * 60)
    print("Trading Pair Configuration Regenerator")
    print("=" * 60)
    print()
    
    # Check if bot_settings.json exists
    bot_settings_file = "config/bot_settings.json"
    if not os.path.exists(bot_settings_file):
        print(f"ERROR: {bot_settings_file} not found!")
        print("Please create bot_settings.json first.")
        return 1
    
    # Load bot_settings
    with open(bot_settings_file, "r") as f:
        bot_settings = json.load(f)
    
    # Display current settings
    print("Current settings:")
    print(f"  Sell coins ({len(bot_settings['sell_coins'])}): {', '.join(bot_settings['sell_coins'])}")
    print(f"  Buy coins ({len(bot_settings['buy_coins'])}): {', '.join(bot_settings['buy_coins'])}")
    
    limit_to_coins = bot_settings.get('limit_to_coins', [])
    if limit_to_coins:
        print(f"  Limit to coins: {', '.join(limit_to_coins)}")
        print(f"  → Will generate pairs containing: {' or '.join(limit_to_coins)}")
    else:
        print(f"  Limit to coins: (none - will generate all pairs)")
    
    print()
    
    # Calculate expected pair count
    sell_coins = set(bot_settings['sell_coins'])
    buy_coins = set(bot_settings['buy_coins'])
    
    if limit_to_coins:
        # Count pairs that include at least one limited coin
        expected_pairs = 0
        for base in sell_coins:
            for rel in buy_coins:
                if base != rel:
                    if base in limit_to_coins or rel in limit_to_coins:
                        expected_pairs += 1
    else:
        expected_pairs = len(sell_coins) * len(buy_coins) - len(sell_coins & buy_coins)
    
    print(f"Expected to generate: {expected_pairs} trading pairs")
    print()
    
    # Backup existing params file if it exists
    params_file = "config/makerbot_command_params.json"
    if os.path.exists(params_file):
        backup_file = params_file + ".backup"
        print(f"Creating backup: {backup_file}")
        with open(params_file, "r") as f:
            content = f.read()
        with open(backup_file, "w") as f:
            f.write(content)
        print()
    
    # Generate new configuration
    print("Generating new configuration...")
    config = Config()
    config.create_bot_params(bot_settings)
    
    # Verify the output
    with open(params_file, "r") as f:
        params = json.load(f)
    
    actual_pairs = len(params['cfg'])
    
    print()
    print("=" * 60)
    print("✓ Configuration regenerated successfully!")
    print("=" * 60)
    print(f"Generated {actual_pairs} trading pairs")
    
    if actual_pairs != expected_pairs:
        print(f"WARNING: Expected {expected_pairs} pairs but generated {actual_pairs}")
    
    print()
    print("Sample pairs (first 10):")
    for i, pair in enumerate(sorted(params['cfg'].keys())[:10]):
        print(f"  {i+1}. {pair}")
    
    if actual_pairs > 10:
        print(f"  ... and {actual_pairs - 10} more")
    
    print()
    print(f"Configuration saved to: {params_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


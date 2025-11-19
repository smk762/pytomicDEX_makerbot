#!/usr/bin/env python3
"""
Test script for the new ActivationManager integration.

This script tests the activation manager's ability to build activation
commands on-the-fly from coins_config.json without relying on pre-downloaded
activation commands.
"""

import sys
from models import Dex


def test_coin_activation_commands():
    """Test activation command generation for various coin types."""
    print("=" * 60)
    print("Testing ActivationManager Integration")
    print("=" * 60)
    
    try:
        dex = Dex()
        print("✓ Dex initialized with ActivationManager")
        print()
        
        # Test cases: (ticker, expected_method_prefix, description)
        test_cases = [
            ("BTC", "task::enable_utxo::init", "UTXO coin"),
            ("ETH", "task::enable_eth::init", "ETH platform coin"),
            ("ATOM", "task::enable_tendermint::init", "Tendermint coin"),
            ("USDT-ERC20", "enable_erc20", "ERC20 token"),
            ("KMD", "task::enable_utxo::init", "Another UTXO coin"),
        ]
        
        passed = 0
        failed = 0
        
        for ticker, expected_method, description in test_cases:
            try:
                print(f"Testing {ticker} ({description})...")
                activation_cmd = dex.get_activation_command(ticker)
                
                if not activation_cmd:
                    print(f"  ✗ Failed: No activation command generated")
                    failed += 1
                    continue
                
                method = activation_cmd.get("method", "")
                has_params = "params" in activation_cmd
                params = activation_cmd.get("params", {})
                ticker_in_params = params.get("ticker", "N/A")
                
                if method.startswith(expected_method.split("::")[0]):
                    print(f"  ✓ Method: {method}")
                    print(f"    - Has params: {has_params}")
                    print(f"    - Ticker in params: {ticker_in_params}")
                    passed += 1
                else:
                    print(f"  ✗ Unexpected method: {method}")
                    print(f"    Expected: {expected_method}")
                    failed += 1
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
                failed += 1
            
            print()
        
        print("=" * 60)
        print(f"Results: {passed} passed, {failed} failed")
        print("=" * 60)
        
        if failed == 0:
            print("\n✅ All tests passed successfully!")
            return 0
        else:
            print(f"\n❌ {failed} test(s) failed")
            return 1
            
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(test_coin_activation_commands())


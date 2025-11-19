# Activation Manager Fixes Summary

## Overview
Three critical issues have been identified and fixed in the activation manager integration.

---

## Fix #1: SIA Server URL - Dynamic Configuration ✅

### Issue
SIA activation was using a hardcoded static server URL instead of sourcing from `coins_config.json`.

### Files Modified
- `activation_manager.py` (lines 543-575)

### Changes
```python
# Before
"server_url": "https://sia-walletd.komodo.earth/"  # Static

# After
server_url = "Not found for {ticker} in coins_config.json!"  # Default
if protocol_info.nodes:
    nodes = self._normalize_eth_nodes(protocol_info.nodes)
    if nodes and nodes[0].get("url"):
        server_url = nodes[0]["url"]  # From coins_config.json
```

### Benefits
- Dynamic server URLs from `coins_config.json`
- Different testnets (SC, SCZEN) use correct URLs
- `required_confirmations` also sourced from config

### Test Results
```
SC:    https://api.siascan.com/wallet/api ✓
SCZEN: https://api.siascan.com/zen/wallet/api ✓
```

---

## Fix #2: Case-Sensitive Ticker Lookup ✅

### Issue
Coins with special suffixes like `-segwit`, `-bchd` were failing because the code was uppercasing them, but `coins_config.json` stores them with lowercase suffixes.

**Error**: `Failed to activate DGB-segwit: Unsupported protocol type: UNKNOWN for ticker: DGB-SEGWIT`

### Affected Coins
52 coins with case-sensitive suffixes:
- `DGB-segwit`, `LTC-segwit`, `BTC-segwit`, `VTC-segwit`
- `BCH-bchd`, `ARRR-segwit`, `DASH-segwit`
- And 45+ more...

### Files Modified
1. `coins_config_manager.py` (lines 62-80)
2. `activation_manager.py` (multiple locations)

### Changes

#### coins_config_manager.py
```python
# Before
def get_coin_config(self, ticker: str):
    return self._coins_config.get(ticker.upper())  # Always uppercase

# After
def get_coin_config(self, ticker: str):
    # First try exact match (preserves case)
    config = self._coins_config.get(ticker)
    if config:
        return config
    # Fallback to uppercase for backwards compatibility
    return self._coins_config.get(ticker.upper())
```

#### activation_manager.py
Removed `.upper()` calls when passing tickers to config lookups:
- `build_activation_request()`
- `build_token_activation_request()`
- `update_nodes_in_request()`

### Backwards Compatibility
- Exact match tried first (e.g., "DGB-segwit")
- Uppercase fallback for regular coins (e.g., "BTC")
- All existing code continues to work

### Test Results
```
DGB-segwit: ✓ Activates successfully (case preserved)
BTC:        ✓ Still works (uppercase fallback)
```

---

## Fix #3: SIA Task Method Prefix ✅

### Issue
SIA activation was using `enable_sia::init` but KDF expects `task::enable_sia::init`.

**Error**: `No such method: enable_sia::init`

### Files Modified
- `activation_manager.py` (lines 571, 770)

### Changes
```python
# Init method (line 571)
- method="enable_sia::init"
+ method="task::enable_sia::init"

# Status method (line 770)
- return "enable_sia::status"
+ return "task::enable_sia::status"
```

### Test Results
```
SC activation:
✓ Method: task::enable_sia::init
✓ Status method: task::enable_sia::status
```

---

## Comprehensive Test Results

All 7 test cases passing:

| Ticker | Type | Method | Status |
|--------|------|--------|--------|
| BTC | UTXO | `task::enable_utxo::init` | ✅ |
| ETH | Platform | `task::enable_eth::init` | ✅ |
| ATOM | Tendermint | `task::enable_tendermint::init` | ✅ |
| USDT-ERC20 | Token | `enable_erc20` | ✅ |
| DGB-segwit | Case-sensitive | `task::enable_utxo::init` | ✅ |
| SC | SIA | `task::enable_sia::init` | ✅ |
| SCZEN | SIA Testnet | `task::enable_sia::init` | ✅ |

```
RESULTS: 7/7 passed, 0/7 failed
🎉 ALL TESTS PASSED! 🎉
```

---

## Files Modified Summary

| File | Lines | Change |
|------|-------|--------|
| `activation_manager.py` | 543-575 | SIA server URL from config |
| `activation_manager.py` | 571 | SIA method prefix |
| `activation_manager.py` | 770 | SIA status method prefix |
| `activation_manager.py` | 465-489 | Remove ticker uppercasing |
| `activation_manager.py` | 669-731 | Remove ticker uppercasing |
| `activation_manager.py` | 293-311 | Remove ticker uppercasing |
| `coins_config_manager.py` | 62-80 | Case-sensitive lookup |

---

## Documentation Created

1. `SIA_ACTIVATION_FIX.md` - Details on SIA server URL fix
2. `CASE_SENSITIVE_TICKER_FIX.md` - Details on case-sensitivity fix
3. `FIXES_SUMMARY.md` - This comprehensive summary

---

## Migration Notes

**No action required** - All fixes are backwards compatible:
- Existing code continues to work
- Case-sensitive coins now work correctly
- SIA coins activate properly
- Server URLs dynamically configured

---

**All fixes completed and tested on November 19, 2025**


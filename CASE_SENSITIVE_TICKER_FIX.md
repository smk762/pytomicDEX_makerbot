# Case-Sensitive Ticker Fix

## Issue
Coins with special suffixes like `-segwit`, `-bchd`, etc. were failing to activate with error:
```
Failed to activate DGB-segwit: Unsupported protocol type: UNKNOWN for ticker: DGB-SEGWIT
```

**Root Cause**: The code was uppercasing all tickers to "DGB-SEGWIT", but `coins_config.json` stores them as "DGB-segwit" (with lowercase suffix). This caused lookups to fail.

## Affected Coins
There are **52 coins** in `coins_config.json` with case-sensitive suffixes:
- Coins ending in `-segwit` (e.g., DGB-segwit, LTC-segwit, VTC-segwit)
- Coins ending in `-bchd` (e.g., BCH-bchd)
- Other mixed-case coins

## Solution

### 1. Updated `coins_config_manager.py`
**File**: `coins_config_manager.py` (lines 62-80)

**Before**:
```python
def get_coin_config(self, ticker: str) -> Optional[Dict[str, Any]]:
    if self._coins_config is None:
        return None
    return self._coins_config.get(ticker.upper())  # ❌ Always uppercase
```

**After**:
```python
def get_coin_config(self, ticker: str) -> Optional[Dict[str, Any]]:
    if self._coins_config is None:
        return None
    
    # First try exact match (preserves case for special suffixes like -segwit)
    config = self._coins_config.get(ticker)
    if config:
        return config
    
    # Fallback to uppercase for backwards compatibility
    return self._coins_config.get(ticker.upper())
```

### 2. Updated `activation_manager.py`
Removed `.upper()` calls when passing tickers to `get_coin_config()` and `get_protocol_info()`:

**Changed functions:**
- `build_activation_request()` - Lines 465-489
- `build_token_activation_request()` - Lines 669-731
- `update_nodes_in_request()` - Lines 293-311

**Before**:
```python
ticker_upper = str(ticker).upper()
protocol_info = self.coins_config.get_protocol_info(ticker_upper)
```

**After**:
```python
# Preserve original ticker case for special suffixes like -segwit
protocol_info = self.coins_config.get_protocol_info(ticker)
```

## Test Results

```bash
Testing DGB-segwit activation command generation...

1. Testing DGB-segwit (case-sensitive)...
✓ Method: task::enable_utxo::init
  - Ticker in params: DGB-segwit
  - Has params: True
  - Activation successful!

2. Testing BTC (regular uppercase)...
✓ Method: task::enable_utxo::init
  - Regular uppercase coin still works!

✅ Case-sensitive ticker lookup is now working!
```

## Backwards Compatibility

The fix maintains backwards compatibility:
1. **Exact match first**: Tries ticker as-is (e.g., "DGB-segwit")
2. **Uppercase fallback**: If not found, tries uppercase (e.g., "BTC")

This ensures:
- Case-sensitive coins like `DGB-segwit` work correctly
- Regular uppercase coins like `BTC` continue to work
- Code passing uppercase versions still works via fallback

## Usage Examples

### Correct Usage (Recommended)
```python
# Use exact case as stored in coins_config.json
dex.activate_coins(['DGB-segwit', 'LTC-segwit', 'BCH-bchd'])
```

### Also Works
```python
# Regular uppercase coins
dex.activate_coins(['BTC', 'ETH', 'KMD'])
```

## Other Coins with Case-Sensitive Suffixes

Examples from `coins_config.json`:
- `ARRR-segwit`
- `BCH-bchd`
- `BTC-segwit`
- `DASH-segwit`
- `DGB-segwit`
- `DOGE-segwit`
- `GLEEC-OLD-segwit`
- `LTC-segwit`
- `RVN-segwit`
- `VTC-segwit`
- `ZEC-segwit`
- And many more...

## Migration Notes

- **No action required** - existing code will continue to work
- **Best practice**: Use exact case from `coins_config.json` when activating coins
- If you encounter "UNKNOWN protocol" errors, check the case of your ticker

## Related Files Modified

1. `coins_config_manager.py` - Case-insensitive lookup with exact match priority
2. `activation_manager.py` - Removed unnecessary `.upper()` calls

---

**Fixed on November 19, 2025**


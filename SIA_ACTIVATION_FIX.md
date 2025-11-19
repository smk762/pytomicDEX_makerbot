# SIA Activation Fix

## Issue
The SIA coin activation in `activation_manager.py` was using a hardcoded static server URL:
```python
"server_url": "https://sia-walletd.komodo.earth/"
```

This should be sourced dynamically from `coins_config.json` like other protocols do.

## Solution
Updated `_build_sia_activation()` method to:
1. Read server URL from the coin's `nodes` configuration in `coins_config.json`
2. Read `required_confirmations` from the coin configuration
3. Use hardcoded values as fallback defaults only

## Changes Made

### File: `activation_manager.py`

**Before:**
```python
def _build_sia_activation(self, ticker: str, protocol_info: CoinProtocolInfo) -> ActivationRequest:
    """Build SIA coin activation request."""
    params = {
        "activation_params": {
            "client_conf": {
                "headers": {},
                "server_url": "https://sia-walletd.komodo.earth/"  # ❌ Hardcoded
            },
            "required_confirmations": 3,  # ❌ Hardcoded
            "tx_history": True
        },
        "client_id": 0,
        "ticker": ticker
    }
    ...
```

**After:**
```python
def _build_sia_activation(self, ticker: str, protocol_info: CoinProtocolInfo) -> ActivationRequest:
    """Build SIA coin activation request."""
    # Get server URL from nodes configuration
    server_url = "https://sia-walletd.komodo.earth/"  # Default fallback
    
    if protocol_info.nodes:
        # Use the first node URL from configuration
        nodes = self._normalize_eth_nodes(protocol_info.nodes)
        if nodes and nodes[0].get("url"):
            server_url = nodes[0]["url"]  # ✅ From coins_config.json
    
    # Get required confirmations from protocol info or use default
    required_confirmations = protocol_info.required_confirmations or 3  # ✅ From coins_config.json
    
    params = {
        "activation_params": {
            "client_conf": {
                "headers": {},
                "server_url": server_url
            },
            "required_confirmations": required_confirmations,
            "tx_history": True
        },
        "client_id": 0,
        "ticker": ticker
    }
    ...
```

## Test Results

```
Testing SC (Siacoin)...
✓ Method: enable_sia::init
  - Server URL: https://api.siascan.com/wallet/api
  - Required confirmations: 1
  - URL from coins_config.json: True

Testing SCZEN (Siacoin Zen Testnet)...
✓ Method: enable_sia::init
  - Server URL: https://api.siascan.com/zen/wallet/api
  - URL from coins_config.json (zen): True
```

## Benefits

1. **Dynamic Configuration**: Server URLs are now sourced from the latest `coins_config.json`
2. **Testnet Support**: Different testnets (like SCZEN) automatically use their correct server URLs
3. **Proper Confirmations**: Each coin uses its specified confirmation count
4. **Consistency**: SIA now follows the same pattern as UTXO, ETH, and Tendermint coins
5. **Easy Updates**: Server URLs can be updated by updating `coins_config.json` without code changes

## Configuration Example

From `coins_config.json`:

```json
{
    "SC": {
        "coin": "SC",
        "type": "SIA",
        "name": "Siacoin",
        "required_confirmations": 1,
        "nodes": [
            {
                "url": "https://api.siascan.com/wallet/api"
            }
        ]
    },
    "SCZEN": {
        "coin": "SCZEN",
        "type": "SIA",
        "name": "Siacoin Zen Testnet",
        "required_confirmations": 1,
        "nodes": [
            {
                "url": "https://api.siascan.com/zen/wallet/api"
            }
        ]
    }
}
```

---

**Fixed on November 19, 2025**


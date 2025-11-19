# ActivationManager Integration

## Overview

The old activation system that relied on downloading pre-built activation commands from `http://stats.kmd.io/api/atomicdex/activation_commands/` has been replaced with a new on-the-fly activation command builder using the `activation_manager.py` module.

## Changes Made

### 1. New Files Created

- **`coins_config_manager.py`**: Manages coin configuration data from `coins_config.json`
  - `CoinsConfigManager` class: Loads and provides access to coin configurations
  - `CoinProtocolInfo` dataclass: Represents protocol information for coins
  - Methods for checking if a ticker is a token, getting protocol info, etc.

- **`lib_kdf/kdf_method.py`**: Utility functions for KDF API methods
  - `extract_ticker_from_request()`: Extracts ticker symbols from request data

- **`lib_kdf/__init__.py`**: Package initialization for KDF utilities

- **`test_activation_manager.py`**: Comprehensive test script for the integration

### 2. Modified Files

#### `const.py`
- **Removed**: Download of activation commands from remote URL
- **Removed**: `ACTIVATE_COMMANDS` global variable
- **Added**: Download of `coins_config.json` alongside the existing `coins` file
- **Added**: `COINS_CONFIG_FILE` and `COINS_CONFIG_URL` constants

#### `models.py`
- **Added**: Import of `ActivationManager` and `Path`
- **Removed**: Import of `ACTIVATE_COMMANDS`
- **Modified**: `Dex.__init__()` - Now initializes an `ActivationManager` instance
- **Modified**: `Dex.activate_coins()` - Now uses the activation manager's methods
- **Modified**: `Dex.get_activation_command()` - Now builds commands on-the-fly

#### `helpers.py`
- **Removed**: Import of `ACTIVATE_COMMANDS`
- **Modified**: `get_activate_command()` - Now creates a temporary `Dex` instance to build commands

#### `activation_manager.py`
- **Updated**: Import paths to use `lib_kdf` instead of `models` (to avoid naming conflict)

## How It Works

### Old Flow
1. On startup, download pre-built activation commands from remote URL
2. Save to `activate_commands.json` as fallback
3. Look up activation command for a coin from the downloaded dictionary
4. Use the pre-built command to activate the coin

### New Flow
1. On startup, download `coins_config.json` (comprehensive coin configuration)
2. When activating a coin:
   - Detect the coin's protocol type (UTXO, ETH, Tendermint, etc.)
   - Check if it's a token (and identify its parent coin if so)
   - Build the appropriate activation command structure on-the-fly
   - Handle parent coin activation for tokens automatically
   - Execute the activation with proper task tracking

## Benefits

1. **Always Up-to-Date**: Commands are built from the latest `coins_config.json`
2. **More Flexible**: Can handle new protocols without updating activation commands
3. **Better Error Handling**: More detailed error messages and activation status tracking
4. **Automatic Token Handling**: Automatically activates parent coins for tokens
5. **HD Wallet Support**: Properly respects the `enable_hd` setting from `MM2.json`

## Testing

Run the test script to verify the integration:

```bash
python3 test_activation_manager.py
```

This tests activation command generation for:
- UTXO coins (BTC, KMD)
- ETH platform coins
- Tendermint coins (ATOM)
- ERC20 tokens (USDT-ERC20)

## Backwards Compatibility

The `get_activation_command()` function in both `models.py` and `helpers.py` has been preserved for backwards compatibility. It now uses the activation manager internally but maintains the same interface.

## Configuration Requirements

The system requires:
1. `mm2/coins_config.json` - Downloaded automatically on startup
2. `config/MM2.json` - Must have `rpc_password` set
3. The `enable_hd` setting in `MM2.json` is respected

## Usage Example

```python
from models import Dex

# Initialize Dex (activation manager is created automatically)
dex = Dex()

# Activate coins (works with both coins and tokens)
dex.activate_coins(['BTC', 'ETH', 'USDT-ERC20', 'ATOM'])

# Or get activation command without executing
activation_cmd = dex.get_activation_command('BTC')
print(activation_cmd)
```

## Troubleshooting

If you encounter issues:

1. **Import errors**: Make sure all new files are in place:
   - `coins_config_manager.py`
   - `lib_kdf/kdf_method.py`
   - `lib_kdf/__init__.py`

2. **Missing coins_config.json**: Run the application once to download it, or manually download from:
   ```
   https://raw.githubusercontent.com/KomodoPlatform/coins/master/utils/coins_config.json
   ```

3. **Activation failures**: Check that `MM2.json` has a valid `rpc_password` and the MM2/KDF instance is running

## Migration Notes

No manual migration is needed. The old `activate_commands.json` file is no longer used and can be safely deleted. The system will automatically use the new activation manager on the next run.


# limit_to_coins Feature Documentation

## Overview

The `limit_to_coins` feature in `bot_settings.json` allows you to filter which trading pairs are generated in `makerbot_command_params.json`. This is useful when you want to focus on trading specific coins without generating configurations for all possible pairs.

## How It Works

### Configuration

In `config/bot_settings.json`, you'll find the `limit_to_coins` field:

```json
{
  "sell_coins": ["BCH", "DASH", "LTC-segwit", "AVAX", "KMD", "DGB-segwit", "DOGE", "MATIC", "USDC-PLG20", "SC"],
  "buy_coins": ["BCH", "DASH", "AVAX", "LTC-segwit", "KMD", "DGB-segwit", "DOGE", "MATIC", "USDC-PLG20", "SC"],
  "limit_to_coins": ["SC"],
  ...
}
```

### Behavior

**When `limit_to_coins` is empty (`[]`):**
- Generates all possible pair combinations between `sell_coins` and `buy_coins`
- Example: With 10 coins in each list, generates 90 pairs (10×10 - 10 same-coin pairs)

**When `limit_to_coins` contains coins (e.g., `["SC"]`):**
- Only generates pairs where at least one of the coins is in the `limit_to_coins` list
- Example: With `["SC"]`, only generates pairs like:
  - `SC/BTC-segwit`
  - `SC/BCH`
  - `BCH/SC`
  - `DOGE/SC`
  - etc.

## Examples

### Example 1: Focus on SC trading
```json
"limit_to_coins": ["SC"]
```
Result: 18 pairs (all pairs involving SC)

### Example 2: Focus on multiple coins
```json
"limit_to_coins": ["SC", "KMD"]
```
Result: Pairs that include SC or KMD (or both)
- `SC/BCH`, `KMD/BCH`, `SC/KMD`, `KMD/SC`, etc.

### Example 3: No limitation (all pairs)
```json
"limit_to_coins": []
```
Result: 90 pairs (all possible combinations)

## Regenerating Configuration

Whenever you modify `bot_settings.json` (including `limit_to_coins`), you need to regenerate the trading pair configuration. The bot will typically do this automatically when it starts, or you can trigger it through the TUI.

## Implementation Details

The filtering logic is implemented in the `create_bot_params()` method in `models.py`. When generating pairs:

1. It reads the `limit_to_coins` setting from `bot_settings.json`
2. For each potential pair (base/rel):
   - If `limit_to_coins` is empty: include the pair
   - If `limit_to_coins` is not empty: only include if base OR rel is in `limit_to_coins`
3. Preserves custom settings from existing pair configurations that pass the filter
4. Removes pairs that don't match the filter

## Benefits

- **Reduced complexity**: Focus on specific trading pairs without manual config editing
- **Faster operations**: Fewer pairs means less processing overhead
- **Better focus**: Concentrate liquidity on specific coins
- **Easy switching**: Simply update one field to change your trading focus

## Notes

- The filter applies to both base and rel coins, so pairs will be included if either side matches
- Existing custom settings for pairs (min/max volume, spread, etc.) are preserved when they pass the filter
- Pairs that don't match the filter are removed from the configuration


#!/usr/bin/env python3
from lib_atomicdex import *

# Documentation: https://developers.komodoplatform.com/basic-docs/atomicdex-api-legacy/coin_activation.html#native-mode-activation
if len(sys.argv) > 1:
    coins_list = []
    for i in range(1,len(sys.argv)):
        coins_list.append(sys.argv[i])
    activate_coins(coins_list)
else:
    status_print(f"No parameters detected (e.g. ./activate.py KMD BTC TKL)! Using coins in makerbot_settings.json...")
    coins_list = list(set(BUY_COINS + SELL_COINS))
    activate_coins(coins_list)
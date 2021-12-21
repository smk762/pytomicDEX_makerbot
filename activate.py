#!/usr/bin/env python3
from lib_atomicdex import *

# Documentation: https://developers.komodoplatform.com/basic-docs/atomicdex-api-legacy/coin_activation.html#native-mode-activation
if len(sys.argv) > 1:
    coins_list = []
    for i in range(1,len(sys.argv)):
        coins_list.append(sys.argv[i])
    activate_coins(coins_list)
else:
    makerbot_settings = load_makerbot_settings()
    status_print(f"No parameters detected (e.g. ./activate.py KMD BTC TKL)! Using coins in makerbot_settings.json...")
    coins_list = list(set(makerbot_settings["buy_coins"] + makerbot_settings["sell_coins"]))
    activate_coins(coins_list)
#!/usr/bin/env python3
import sys
from const import BOT_SETTINGS_FILE
from helpers import status_print
from models import MakerBot, Dex


dex = Dex()
# Documentation: https://developers.komodoplatform.com/basic-docs/atomicdex-api-legacy/coin_activation.html#native-mode-activation
# Usage: './activate.py KMD DGB LTC'

if len(sys.argv) > 1:
    coins_list = []
    for i in range(1, len(sys.argv)):
        coins_list.append(sys.argv[i])
    dex.activate_coins(coins_list)
else:
    bot = MakerBot()
    status_print(f"No parameters detected! Using coins in {BOT_SETTINGS_FILE}...")
    coins_list = list(set(bot.settings["buy_coins"] + bot.settings["sell_coins"]))
    dex.activate_coins(coins_list)

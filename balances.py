#!/usr/bin/env python3
from lib_atomicdex import *

coins_list = get_enabled_coins_list()

if len(coins_list) == 0:
    status_print("No coins are activated!")
else:
    # Documentation: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-api-legacy/my_balance.html
    get_balances_table(coins_list)



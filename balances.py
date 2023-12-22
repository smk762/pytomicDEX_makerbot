#!/usr/bin/env python3
from helpers import status_print
from models import Dex, Tables

dex = Dex()
tables = Tables()

coins_list = dex.enabled_coins_list

if len(coins_list) == 0:
    status_print("No coins are activated!")
else:
    # Documentation: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-api-legacy/my_balance.html
    tables.balances(coins_list)

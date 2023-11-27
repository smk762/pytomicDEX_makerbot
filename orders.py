#!/usr/bin/env python3
from models import Table, Dex

# Documentation reference: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-api-legacy/my_orders.html
dex = Dex()
table = Table()

table.orders(dex.api.orders)

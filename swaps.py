#!/usr/bin/env python3
import sys
from models import Table, Dex

table = Table()

# Documentation reference: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-api-legacy/my_recent_swaps.html
if len(sys.argv) > 1:
    limit = int(sys.argv[1])
    table.swaps_summary(Dex().api.rpc("my_recent_swaps").json(), limit)
else:
    table.swaps_summary(Dex().api.rpc("my_recent_swaps").json())

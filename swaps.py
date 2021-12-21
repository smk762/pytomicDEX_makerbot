#!/usr/bin/env python3
from lib_atomicdex import *

# Documentation reference: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-api-legacy/my_recent_swaps.html
if len(sys.argv) > 1:
    limit = int(sys.argv[1])
    get_swaps_summary_table(limit)
else:
    get_swaps_summary_table()

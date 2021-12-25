#!/usr/bin/env python3
from lib_atomicdex import *

resp = stop_mm2()
if 'error' in resp:
    error_print(resp)
elif "success" in resp:
    status_print("AtomicDEX-API has stopped.")
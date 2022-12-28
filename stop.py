#!/usr/bin/env python3
from lib_atomicdex import stop_mm2

resp = stop_mm2()
if 'error' in resp:
    error_print(resp)
elif "success" in resp:
    status_print("AtomicDEX-API has stopped.")

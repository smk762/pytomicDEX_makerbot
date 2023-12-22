#!/usr/bin/env python3
from helpers import status_print, error_print
from models import Dex

dex = Dex()
resp = dex.quit()
if "error" in resp:
    error_print(resp)
elif "success" in resp:
    status_print("Komodo DeFi Framework has stopped.")

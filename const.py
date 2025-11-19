#!/usr/bin/env python3
import os
import sys
import json
import time
import string
import random
import os.path
from zipfile import ZipFile
import platform
import requests
from os.path import expanduser

ACTIVE_TASKS = {}
HOME = expanduser("~")
VALID_OP_SYS = ["Linux", "Darwin", "Windows"]
SCRIPT_PATH = os.path.realpath(os.path.dirname(__file__))

OP_SYS = platform.system()
if OP_SYS not in VALID_OP_SYS:
    print(f"Invalid OS, must be in {VALID_OP_SYS}")
    sys.exit()

if OP_SYS.lower() == "windows":
    MM2BIN = f"{SCRIPT_PATH}/mm2/kdf.exe"
else:
    MM2BIN = f"{SCRIPT_PATH}/mm2/kdf"

ERROR_EVENTS = [
    "StartFailed",
    "NegotiateFailed",
    "TakerFeeValidateFailed",
    "MakerPaymentTransactionFailed",
    "MakerPaymentDataSendFailed",
    "MakerPaymentWaitConfirmFailed",
    "TakerPaymentValidateFailed",
    "TakerPaymentWaitConfirmFailed",
    "TakerPaymentSpendFailed",
    "TakerPaymentSpendConfirmFailed",
    "MakerPaymentWaitRefundStarted",
    "MakerPaymentRefunded",
    "MakerPaymentRefundFailed",
]

# NOTE: Users should set this to their own desired url. The URL below is for refrence only, use at your own risk.
# PRICE_URL = "https://prices.cipig.net:1717/api/v2/tickers?expire_at=600"
PRICE_URLS = [
    "https://prices.komodian.info/api/v2/tickers?expire_at=900",
    "https://defi-stats.komodo.earth/api/v3/prices/tickers_v2?expire_at=900"
]

BOT_SETTINGS_FILE = f"{SCRIPT_PATH}/config/bot_settings.json"
BOT_PARAMS_FILE = f"{SCRIPT_PATH}/config/makerbot_command_params.json"
MM2_LOG_FILE = f"{SCRIPT_PATH}/logs/mm2_output.log"
MM2_JSON_FILE = f"{SCRIPT_PATH}/config/MM2.json"
TEMP_MM2_JSON_FILE = f"{SCRIPT_PATH}/scan/MM2.json"
USERPASS_FILE = f"{SCRIPT_PATH}/config/userpass"
SEEDS_FILE = f"{SCRIPT_PATH}/scan/seed_phrases.json"

# Activation manager will be initialized per instance
# No longer downloading activation commands - they will be built on-the-fly
# from coins_config.json via the ActivationManager

# Update coins files on launch
COINS_FILE = f"{SCRIPT_PATH}/coins"
COINS_URL = "https://raw.githubusercontent.com/KomodoPlatform/coins/master/coins"
COINS_CONFIG_FILE = f"{SCRIPT_PATH}/mm2/coins_config.json"
COINS_CONFIG_URL = "https://raw.githubusercontent.com/KomodoPlatform/coins/master/utils/coins_config.json"

try:
    print("Updating coins files...")
    # Download original coins file for backwards compatibility
    coins = requests.get(COINS_URL, timeout=5).json()
    with open(COINS_FILE, "w", encoding="utf-8") as f:
        json.dump(coins, f, ensure_ascii=False, indent=4)
    
    # Download coins_config.json for activation manager
    coins_config = requests.get(COINS_CONFIG_URL, timeout=5).json()
    with open(COINS_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(coins_config, f, ensure_ascii=False, indent=4)
    
    print("Coins files updated successfully.")
except Exception as e:
    print(f"Warning: Unable to update coins files: {e}")
    if not os.path.exists(COINS_FILE) or not os.path.exists(COINS_CONFIG_FILE):
        print("Error: Required coins configuration files are missing.")
        print("Please check your internet connection, or report this to smk on Discord.")
        sys.exit()

with open(COINS_FILE, "r", encoding="utf-8") as f:
    coins_data = json.load(f)
COINS_LIST = [i["coin"] for i in coins_data if i["mm2"] == 1]

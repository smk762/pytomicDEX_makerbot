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
    MM2BIN = f"{SCRIPT_PATH}/mm2/mm2.exe"
else:
    MM2BIN = f"{SCRIPT_PATH}/mm2/mm2"

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
#PRICES_URL = "https://prices.cipig.net:1717/api/v2/tickers?expire_at=600"
PRICES_URL = "https://prices.komodo.earth/api/v2/tickers"

BOT_SETTINGS_FILE = f"{SCRIPT_PATH}/config/bot_settings.json"
BOT_PARAMS_FILE = f"{SCRIPT_PATH}/config/makerbot_command_params.json"
MM2_LOG_FILE = f"{SCRIPT_PATH}/logs/mm2_output.log"
MM2_JSON_FILE = f"{SCRIPT_PATH}/config/MM2.json"
TEMP_MM2_JSON_FILE = f"{SCRIPT_PATH}/scan/MM2.json"
USERPASS_FILE = f"{SCRIPT_PATH}/config/userpass"
SEEDS_FILE = f"{SCRIPT_PATH}/scan/seed_phrases.json"

# Update activation commands file on launch
ACTIVATION_FILE = f"{SCRIPT_PATH}/activate_commands.json"
ACTIVATION_URL = "http://stats.kmd.io/api/atomicdex/activation_commands/"
try:
    ACTIVATE_COMMANDS = requests.get(ACTIVATION_URL).json()["commands"]
    with open(f"{SCRIPT_PATH}/activate_commands.json", "w+") as f:
        json.dump(ACTIVATE_COMMANDS, f, indent=4)
except:
    if os.path.exists(f"{SCRIPT_PATH}/activate_commands.json"):
        ACTIVATE_COMMANDS = json.load(
            open(f"{SCRIPT_PATH}/activate_commands.json", "r")
        )
    else:
        print(
            f"Unable to load {ACTIVATE_COMMANDS}, please check your internet connection, or report this to smk on Discord."
        )
        sys.exit()

# Update coins file on launch
COINS_FILE = f"{SCRIPT_PATH}/coins"
COINS_URL = "https://raw.githubusercontent.com/KomodoPlatform/coins/master/coins"
try:
    print("coins file not found, downloading...")
    coins = requests.get(COINS_URL).json()
    with open(COINS_FILE, "w", encoding="utf-8") as f:
        json.dump(coins, f, ensure_ascii=False, indent=4)
except:
    print(
        f"Unable to load {COINS_FILE}, please check your internet connection, or report this to smk on Discord."
    )
    sys.exit()

with open(COINS_FILE, "r", encoding="utf-8") as f:
    coins_data = json.load(f)
COINS_LIST = [i["coin"] for i in coins_data if i["mm2"] == 1]

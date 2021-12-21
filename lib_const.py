#!/usr/bin/env python3
import os
import io
import sys
import json
import stat
import time
import string
import random
import os.path
from zipfile import ZipFile
import platform
import mnemonic
import requests
from os.path import expanduser


def colorize(string, color):
    colors = {
        'black':'\033[30m',
        'error':'\033[31m',
        'red':'\033[31m',
        'green':'\033[32m',
        'orange':'\033[33m',
        'blue':'\033[34m',
        'purple':'\033[35m',
        'cyan':'\033[36m',
        'lightgrey':'\033[37m',
        'table':'\033[37m',
        'darkgrey':'\033[90m',
        'lightred':'\033[91m',
        'lightgreen':'\033[92m',
        'yellow':'\033[93m',
        'lightblue':'\033[94m',
        'status':'\033[94m',
        'pink':'\033[95m',
        'lightcyan':'\033[96m',
    }
    if color not in colors:
        return str(string)
    else:
        return colors[color] + str(string) + '\033[0m'


def color_input(msg):
  return input(colorize(msg, "orange"))

def table_print(msg):
  print(colorize(msg, "cyan"))

def status_print(msg):
  print(colorize(msg, "status"))

def success_print(msg):
  print(colorize(msg, "green"))

def error_print(msg):
  print(colorize(msg, "error"))

def wait_continue():
  color_input("Press [Enter] to continue...")
   
def generate_rpc_pass(length):
    rpc_pass = ""
    special_chars = ["@", "~", "-", "_", "|", "(", ")", ":", "+"]
    quart = int(length/4)
    while len(rpc_pass) < length:
        rpc_pass += ''.join(random.sample(string.ascii_lowercase, random.randint(1,quart)))
        rpc_pass += ''.join(random.sample(string.ascii_uppercase, random.randint(1,quart)))
        rpc_pass += ''.join(random.sample(string.digits, random.randint(1,quart)))
        rpc_pass += ''.join(random.sample(special_chars, random.randint(1,quart)))
    str_list = list(rpc_pass)
    random.shuffle(str_list)
    return ''.join(str_list)


def get_config(base,rel):
  config_template = {
      "base": "base_coin",
      "rel": "rel_coin",
      "min_volume": {
          "usd":MIN_USD
      },
      "max_volume":  {
          "usd":MAX_USD
      },
      "spread": SPREAD,
      "base_confs": 3,
      "base_nota": True,
      "rel_confs": 3,
      "rel_nota": True,
      "enable": True,
      "price_elapsed_validity": int(PRICES_API_TIMEOUT),
      "check_last_bidirectional_trade_thresh_hold": USE_BIDIRECTIONAL_THRESHOLD
  }
  cfg = config_template.copy()
  cfg.update({
      "base": base,
      "rel": rel, 
  })
  return cfg


def view_makerbot_params():
    with open("makerbot_command_params.json", "r") as f:
        MAKERBOT_PARAMS = json.load(f)
    table_print(f"Prices URL: {MAKERBOT_PARAMS['price_url']}")
    table_print(f"Refresh rate: {MAKERBOT_PARAMS['bot_refresh_rate']} sec")
    for pair in MAKERBOT_PARAMS['cfg']:
        cfg = MAKERBOT_PARAMS['cfg'][pair]
        table_print(f'{pair}: {round((cfg["spread"]-1)*100,3)}% spread, {cfg["min_volume"]["usd"]} min USD, {cfg["max_volume"]["usd"]} max USD')

# Documentation reference: https://developers.komodoplatform.com/basic-docs/atomicdex-api-20-dev/start_simple_market_maker_bot.html
def get_makerbot_params():
    global MAKERBOT_PARAMS
    params = {
        "price_url": PRICES_API,
        "bot_refresh_rate": int(ORDER_REFRESH_RATE)    
    }

    configs = {}
    for base in SELL_COINS:
        for rel in BUY_COINS:
            if base != rel:
                configs.update({
                    f"{base}/{rel}": get_config(base, rel)
                })
    params.update({
        "cfg":configs
    })

    with open('makerbot_command_params.json', 'w', encoding='utf-8') as f:
        json.dump(params, f, ensure_ascii=False, indent=4)

    with open("makerbot_command_params.json", "r") as f:
        MAKERBOT_PARAMS = json.load(f)

    return MAKERBOT_PARAMS


def get_makerbot_settings(update=False):
    global MAKERBOT_SETTINGS
    global BUY_COINS
    global SELL_COINS
    if not os.path.exists("makerbot_settings.json") or update:
        sell_coins = color_input("Enter tickers of coins you want to sell, seperated by a space:\n")
        buy_coins = color_input("Enter tickers of coins you want to buy, seperated by a space:\n")
        min_usd =  color_input("Enter minimum trade value in USD (e.g. 10): ")
        max_usd =  color_input("Enter maximum trade value in USD (e.g. 100): ")
        spread =  color_input("Enter spread percentage (e.g. 5): ")
        refresh_rate =  color_input("How often to update prices in seconds (e.g. 180): ")

        makerbot_conf = {
            "sell_coins": sell_coins.split(" "),
            "buy_coins": buy_coins.split(" "),
            "min_usd": int(min_usd),
            "max_usd": int(max_usd),
            "spread": 1+(float(spread)/100),
            "refresh_rate": refresh_rate,
            "prices_api": PRICES_API,
            "prices_api_timeout": 180,
            "use_bidirectional_threshold": True,
        }

        table_print(json.dumps(makerbot_conf, indent=4))
        resp = color_input("Confirm configuration? [Y/N]: ")

        with open("makerbot_settings.json", "w+") as f:
            json.dump(makerbot_conf, f, indent=4)

    with open("makerbot_settings.json", "r") as f:
        MAKERBOT_SETTINGS = json.load(f)

    BUY_COINS = MAKERBOT_SETTINGS["buy_coins"]
    SELL_COINS = MAKERBOT_SETTINGS["sell_coins"]
    return MAKERBOT_SETTINGS


# Load or Create MM2.json
# Documentation: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-setup/configure-mm2-json.html#mm2-json
def load_MM2_json():
    if os.path.exists("MM2.json"):
        with open("MM2.json", "r") as f:
            MM2_JSON = json.load(f)
    else:
        table_print("Looks like you dont have an MM2.json file, lets create one now...")
        rpc_password = generate_rpc_pass(16)
        mm2_conf = {
            "gui": "NN_SEED",
            "netid": 7777,
            "i_am_seed":False,
            "rpc_password": rpc_password,
            "userhome": "/${HOME#\"/\"}"
        }

        new_seed = color_input("[E]nter seed manually or [G]enerate one? [E/G]: ")
        while new_seed not in ["G", "g", "E", "e"]:
            error_print("Invalid input!")
            new_seed = color_input("[E]nter seed manually or [G]enerate one? [E/G]: ")

        if new_seed in ["E", "e"]:
            passphrase = color_input("Enter a seed phrase: ")
        else:        
            m = mnemonic.Mnemonic('english')
            passphrase = m.generate(strength=256)

        mm2_conf.update({"passphrase": passphrase})

        with open("MM2.json", "w+") as f:
            json.dump(mm2_conf, f, indent=4)
            status_print("MM2.json file created.")

        with open("userpass", "w+") as f:
            f.write(f'userpass="{rpc_password}"')
            status_print("userpass file created.")

    with open("MM2.json", "r") as f:
        MM2_JSON = json.load(f)
    return MM2_JSON


# Download coins if not existing
def get_coins_file():
    if not os.path.exists("coins"):
        status_print("coins file not found, downloading...")
        url = "https://raw.githubusercontent.com/KomodoPlatform/coins/master/coins"
        coins = requests.get(url).json()

        with open('coins', 'w', encoding='utf-8') as f:
            json.dump(coins, f, ensure_ascii=False, indent=4)


HOME = expanduser("~")
SCRIPT_PATH = sys.path[0]
PRICES_API = "https://prices.cipig.net:1717/api/v2/tickers?expire_at=600"
ACTIVATE_COMMANDS = requests.get("http://stats.kmd.io/api/atomicdex/activation_commands/").json()["commands"]

ERROR_EVENTS = [
  "StartFailed", "NegotiateFailed", "TakerFeeValidateFailed", "MakerPaymentTransactionFailed",
  "MakerPaymentDataSendFailed", "MakerPaymentWaitConfirmFailed", "TakerPaymentValidateFailed",
  "TakerPaymentWaitConfirmFailed", "TakerPaymentSpendFailed", "TakerPaymentSpendConfirmFailed",
  "MakerPaymentWaitRefundStarted", "MakerPaymentRefunded", "MakerPaymentRefundFailed"
  ]

VALID_OP_SYS = ['Linux', 'Darwin', 'Windows']
OP_SYS = platform.system()
if OP_SYS not in VALID_OP_SYS:
    error_print(f"Invalid OS, must be in {VALID_OP_SYS}")
    sys.exit()
if OP_SYS == "Windows":
    OP_SYS = "Windows_NT"
    error_print(f"Windows is not currently supported, but you can try using WSL.\n See https://docs.microsoft.com/en-us/windows/wsl/install")
    sys.exit()

# Load or create MM2.json
MM2_JSON = load_MM2_json()
MM2_USERPASS = MM2_JSON["rpc_password"]
MM2_IP = "http://127.0.0.1:7783"

# Get coins file if needed
get_coins_file()

# Setup or load makerbot_settings.json
MAKERBOT_SETTINGS = get_makerbot_settings()
BUY_COINS = MAKERBOT_SETTINGS["buy_coins"]
SELL_COINS = MAKERBOT_SETTINGS["sell_coins"]
MIN_USD = MAKERBOT_SETTINGS["min_usd"]
MAX_USD = MAKERBOT_SETTINGS["max_usd"]
SPREAD = MAKERBOT_SETTINGS["spread"]
ORDER_REFRESH_RATE = MAKERBOT_SETTINGS["refresh_rate"]
PRICES_API_TIMEOUT = MAKERBOT_SETTINGS["prices_api_timeout"]
USE_BIDIRECTIONAL_THRESHOLD = MAKERBOT_SETTINGS["use_bidirectional_threshold"]

# Setup makerbot_params.json
MAKERBOT_PARAMS = get_makerbot_params()


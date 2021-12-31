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

def info_print(msg):
  print(colorize(msg, "orange"))

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


def get_config(base, rel, min_usd, max_usd, spread):
  config_template = {
      "base": "base_coin",
      "rel": "rel_coin",
      "base_confs": 3,
      "base_nota": True,
      "rel_confs": 3,
      "rel_nota": True,
      "enable": True,
      "price_elapsed_validity": 180,
      "check_last_bidirectional_trade_thresh_hold": True
  }
  cfg = config_template.copy()
  cfg.update({
      "base": base,
      "rel": rel,
      "min_volume": {
          "usd":float(min_usd)
      },
      "max_volume":  {
          "usd":float(max_usd)
      },

      "spread": round(spread,4)
  })
  return cfg


def create_makerbot_params(makerbot_settings):
    buy_coins = makerbot_settings["buy_coins"]
    sell_coins = makerbot_settings["sell_coins"]
    min_usd = makerbot_settings["default_min_usd"]
    max_usd = makerbot_settings["default_max_usd"]
    spread = makerbot_settings["default_spread"]
    order_refresh_rate = makerbot_settings["refresh_rate"]
    use_bidirectional_threshold = True
    params = {
        "price_url": PRICES_API,
        "bot_refresh_rate": int(order_refresh_rate)    
    }

    configs = {}
    for base in sell_coins:
        for rel in buy_coins:
            if base != rel:
                configs.update({
                    f"{base}/{rel}": get_config(base, rel, min_usd, max_usd, spread)
                })

    params.update({
        "cfg":configs
    })

    with open('makerbot_command_params.json', 'w', encoding='utf-8') as f:
        json.dump(params, f, ensure_ascii=False, indent=4)


def update_makerbot_pair_params(base, rel, min_usd, max_usd, spread):
    makerbot_params = load_makerbot_params()

    config = get_config(base, rel, min_usd, max_usd, spread)
    makerbot_params["cfg"].update({
        f"{base}/{rel}": config
    })

    with open('makerbot_command_params.json', 'w', encoding='utf-8') as f:
        json.dump(makerbot_params, f, ensure_ascii=False, indent=4)


def update_makerbot_coin_params(coin, side, min_usd, max_usd, spread):
    makerbot_settings = load_makerbot_settings()
    makerbot_params = load_makerbot_params()

    if side == 'base':
        base = coin
        for rel in makerbot_settings["buy_coins"]:
            if base != rel:
                config = get_config(base, rel, min_usd, max_usd, spread)
                makerbot_params["cfg"].update({
                    f"{base}/{rel}": config
                })

    elif side == 'rel':
        rel = coin
        for base in makerbot_settings["sell_coins"]:
            if base != rel:
                config = get_config(base, rel, min_usd, max_usd, spread)
                makerbot_params["cfg"].update({
                    f"{base}/{rel}": config
                })


    with open('makerbot_command_params.json', 'w', encoding='utf-8') as f:
        json.dump(makerbot_params, f, ensure_ascii=False, indent=4)


def get_makerbot_params():
    if not os.path.exists("makerbot_command_params.json"):
        create_makerbot_settings()


def create_makerbot_settings():
    q = "n"
    while q.lower() == "n":
        sell_coins = color_input("Enter tickers of coins you want to sell, seperated by a space:\n")
        buy_coins = color_input("Enter tickers of coins you want to buy, seperated by a space:\n")
        min_usd = color_input("Enter default minimum trade value in USD (e.g. 10): ")
        max_usd = color_input("Enter default maximum trade value in USD (e.g. 100): ")
        spread = color_input("Enter default spread percentage (e.g. 5): ")
        refresh_rate = color_input("How often to update prices in seconds (e.g. 180): ")

        makerbot_settings = {
            "sell_coins": list(set(sell_coins.split(" "))),
            "buy_coins": list(set(buy_coins.split(" "))),
            "default_min_usd": int(min_usd),
            "default_max_usd": int(max_usd),
            "default_spread": 1+(float(spread)/100),
            "refresh_rate": refresh_rate,
            "prices_api": PRICES_API,
            "prices_api_timeout": 180,
            "use_bidirectional_threshold": True,
        }

        table_print(json.dumps(makerbot_settings, indent=4))
        q = color_input("Confirm configuration? [Y/N]: ")

        while q.lower() not in ["y", "n"]:
            error_print("Invalid option!")
            q = color_input("Confirm configuration? [Y/N]: ")

    with open("makerbot_settings.json", "w+") as f:
        json.dump(makerbot_settings, f, indent=4)
    create_makerbot_params(makerbot_settings)


def load_makerbot_settings():
    with open("makerbot_settings.json", "r") as f:
        return json.load(f)


# Documentation reference: https://developers.komodoplatform.com/basic-docs/atomicdex-api-20-dev/start_simple_market_maker_bot.html
def load_makerbot_params():
    with open("makerbot_command_params.json", "r") as f:
        return json.load(f)


def get_makerbot_settings():
    if not os.path.exists("makerbot_settings.json"):
        status_print("\nFirst we need to set up some configs...")
        status_print("\nDon't forget to evaluate your risk tolerance and only trade small amounts you are comfortable with.")
        create_makerbot_settings()



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
            "gui": "pyMakerbot",
            "netid": 7777,
            "rpcport": 7763,
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
            status_print("Be sure to make a secure backup of your seed phrase offline!")

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
MM2_IP = "http://127.0.0.1:7763"

# Get coins file if needed
get_coins_file()

# Setup or load makerbot_settings.json
get_makerbot_settings()

# Setup or create makerbot_params.json
get_makerbot_params()


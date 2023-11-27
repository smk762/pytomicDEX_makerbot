#!/bin/python3
import os
import sys
import stat
import time
import string
import random
import requests
from zipfile import ZipFile
from const import ACTIVATE_COMMANDS, PRICES_URL, OP_SYS, SCRIPT_PATH

def sec_to_hms(sec):
    minutes, seconds = divmod(sec, 60)
    hours, minutes = divmod(minutes, 60)
    periods = [("h", hours), ("m", minutes), ("s", seconds)]
    return " ".join("{}{}".format(int(val), name) for name, val in periods if val)


def get_activate_command(coin):
    for protocol in ACTIVATE_COMMANDS:
        if coin in ACTIVATE_COMMANDS[protocol]:
            return ACTIVATE_COMMANDS[protocol][coin]


def get_valid_input(msg, valid_options):
    q = color_input(msg)
    while q.lower() not in valid_options:
        error_print("Invalid option, try again.")
        q = color_input(msg)
    return q


def get_price(coin, current_prices=None):
    if not current_prices:
        current_prices = requests.get(PRICES_URL).json()
    if "-" in coin:
        coin = coin.split("-")[0]
    if coin in current_prices:
        return float(current_prices[coin]["last_price"])
    else:
        return 0


def download_progress(url, fn):
    with open(fn, "wb") as f:
        r = requests.get(url, stream=True)
        total = r.headers.get("content-length")

        if total is None:
            f.write(r.content)
        else:
            downloaded = 0
            total = int(total)
            for data in r.iter_content(chunk_size=max(int(total / 1000), 1024 * 1024)):
                downloaded += len(data)
                f.write(data)
                done = int(50 * downloaded / total)
                sys.stdout.write(
                    f"\rDownloading {fn}: [{'#' * done}{'.' * (50-done)}] {done*2}%"
                )
                sys.stdout.flush()
    sys.stdout.write("\n")
    return r


def get_short_hash(org, repo, branch):
    url = f"https://api.github.com/repos/{org}/{repo}/branches/{branch}"
    r = requests.get(url)
    try:
        resp = r.json()
        commit_sha = resp["commit"]["sha"]
        return commit_sha[:9]
    except:
        error_print(f"{branch} does not exist!")
        return None


def get_release_assets_info(org, repo):
    releases_url = f"https://api.github.com/repos/{org}/{repo}/releases"
    r = requests.get(releases_url)
    print(releases_url)
    try:
        return r.json()[0]["assets"]
    except:
        error_print(f"{repo} or {org} does not exist!")
        return None


def get_mm2(branch=None):
    assets = get_release_assets_info("komodoplatform", "komodo-defi-framework")
    for asset in assets:
        print(asset)
        if OP_SYS.lower() in asset["browser_download_url"].lower():
            asset_url = asset["browser_download_url"]
            asset_name = asset["name"]
    else:
        error_print("Release not found!")

    download_path = f"{SCRIPT_PATH}/mm2/{asset_name}"
    if not os.path.exists(download_path):
        if asset_url:
            download_progress(asset_url, download_path)
    else:
        status_print(f"{download_path} already downloaded...")

    with ZipFile(download_path, "r") as zf:
        status_print(f"Extracting {download_path}...")
        zf.extractall(os.path.dirname(download_path))
        if OP_SYS.lower() != "windows":
            print("setting perms")
            os.chmod(f"{os.path.dirname(download_path)}/mm2", stat.S_IEXEC)
            
        status_print("Done!")


def sleep_message(msg, sec):
    status_print(msg)
    time.sleep(sec)


def preexec():  # Don't forward signals.
    os.setpgrp()


def get_order_count(orders):
    maker_orders = {}
    taker_orders = {}
    if "result" in orders:
        if "maker_orders" in orders["result"]:
            maker_orders = orders["result"]["maker_orders"]
        if "taker_orders" in orders["result"]:
            taker_orders = orders["result"]["taker_orders"]
    else:
        if "maker_orders" in orders:
            maker_orders = orders["maker_orders"]
        if "taker_orders" in orders:
            taker_orders = orders["taker_orders"]
    order_count = len(maker_orders) + len(taker_orders)
    return maker_orders, taker_orders, order_count


def colorize(string, color):
    colors = {
        "black": "\033[30m",
        "error": "\033[31m",
        "red": "\033[31m",
        "green": "\033[32m",
        "orange": "\033[33m",
        "blue": "\033[34m",
        "purple": "\033[35m",
        "cyan": "\033[36m",
        "lightgrey": "\033[37m",
        "table": "\033[37m",
        "darkgrey": "\033[90m",
        "lightred": "\033[91m",
        "lightgreen": "\033[92m",
        "yellow": "\033[93m",
        "lightblue": "\033[94m",
        "status": "\033[94m",
        "pink": "\033[95m",
        "lightcyan": "\033[96m",
    }
    if color not in colors:
        return str(string)
    else:
        return colors[color] + str(string) + "\033[0m"


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
    quart = int(length / 4)
    while len(rpc_pass) < length:
        rpc_pass += "".join(
            random.sample(string.ascii_lowercase, random.randint(1, quart))
        )
        rpc_pass += "".join(
            random.sample(string.ascii_uppercase, random.randint(1, quart))
        )
        rpc_pass += "".join(random.sample(string.digits, random.randint(1, quart)))
        rpc_pass += "".join(random.sample(special_chars, random.randint(1, quart)))
    str_list = list(rpc_pass)
    random.shuffle(str_list)
    return "".join(str_list)

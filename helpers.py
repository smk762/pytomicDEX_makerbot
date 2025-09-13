#!/bin/python3
import os
import sys
import stat
import time
import json
import string
import random
import requests
from zipfile import ZipFile
from const import PRICE_URLS, OP_SYS, SCRIPT_PATH, MM2_JSON_FILE
from activation import build_activate_command
import re

def sec_to_hms(sec):
    minutes, seconds = divmod(sec, 60)
    hours, minutes = divmod(minutes, 60)
    periods = [("h", hours), ("m", minutes), ("s", seconds)]
    return " ".join("{}{}".format(int(val), name) for name, val in periods if val)


def get_activate_command(coin):
    return build_activate_command(coin)


def get_valid_input(msg, valid_options):
    q = color_input(msg)
    while q.lower() not in valid_options:
        error_print("Invalid option, try again.")
        q = color_input(msg)
    return q


def get_price(coin, current_prices=None):
    if not current_prices:
        current_prices = get_prices()
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


def get_latest_kdf_release_info():
    """Return the latest KDF release JSON (tag_name, html_url, assets, ...). Caches for 1h."""
    now = time.time()
    cache = _LATEST_KDF_CACHE
    cache_age = now - (cache.get("ts") or 0)
    if cache_age < 3600 and cache.get("data"):
        return cache["data"]

    releases_url = "https://api.github.com/repos/KomodoPlatform/komodo-defi-framework/releases"
    try:
        r = requests.get(releases_url, timeout=8)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            latest = data[0]
            _LATEST_KDF_CACHE.update({"ts": now, "data": latest})
            return latest
    except Exception:
        pass
    # Fallback minimal structure
    fallback = {
        "tag_name": "v2.5.1-beta",
        "html_url": "https://github.com/KomodoPlatform/komodo-defi-framework/releases/tag/v2.5.1-beta",
        "assets": [],
    }
    _LATEST_KDF_CACHE.update({"ts": now, "data": fallback})
    return fallback


def get_kdf(branch=None):
    assets = get_latest_kdf_release_info().get("assets", [])
    for asset in assets:
        print(asset)
        if OP_SYS.lower() in asset["browser_download_url"].lower():
            asset_url = asset["browser_download_url"]
            asset_name = asset["name"]
    else:
        error_print("Release not found!")

    # Ensure target directory exists
    target_dir = f"{SCRIPT_PATH}/kdf"
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    download_path = f"{target_dir}/{asset_name}"
    if not os.path.exists(download_path):
        if asset_url:
            download_progress(asset_url, download_path)
    else:
        status_print(f"{download_path} already downloaded...")

    with ZipFile(download_path, "r") as zf:
        status_print(f"Extracting {download_path}...")
        zf.extractall(os.path.dirname(download_path))
        extracted_dir = os.path.dirname(download_path)
        # Determine extracted filename (mm2 or mm2.exe) and rename to kdf/kdf.exe
        old_name = "mm2.exe" if OP_SYS.lower() == "windows" else "mm2"
        new_name = "kdf.exe" if OP_SYS.lower() == "windows" else "kdf"
        old_path = f"{extracted_dir}/{old_name}"
        new_path = f"{extracted_dir}/{new_name}"
        try:
            if os.path.exists(old_path):
                os.replace(old_path, new_path)
        except Exception as e:
            error_print(f"Failed to rename {old_path} to {new_path}: {e}")
        if OP_SYS.lower() != "windows":
            print("setting perms")
            os.chmod(new_path, stat.S_IEXEC)
            
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

def get_prices():
    for i in PRICE_URLS:
        try:
            return requests.get(i).json()
        except Exception as e:
            print(f"Price service at {i} is not responding!")
    return {}

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


# ---- KDF release and terminal formatting helpers ----

_LATEST_KDF_CACHE = {"ts": 0, "data": None}


def format_hyperlink(label, url):
    """Return an OSC 8 hyperlink sequence for supported terminals."""
    # Open hyperlink: ESC ] 8 ; ; URL ESC \
    # Close hyperlink: ESC ] 8 ; ; ESC \
    open_seq = f"\033]8;;{url}\033\\"
    close_seq = "\033]8;;\033\\"
    return f"{open_seq}{label}{close_seq}"


_CSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
_OSC8_RE = re.compile(r"\x1b\]8;;.*?\x1b\\")


def strip_ansi_sequences(text):
    """Strip ANSI CSI and OSC8 sequences for visible-length calculations."""
    text = _OSC8_RE.sub("", text)
    text = _CSI_RE.sub("", text)
    return text


def center_visible(text, width):
    """Center text accounting for non-printing ANSI sequences."""
    visible_len = len(strip_ansi_sequences(text))
    if visible_len >= width:
        return text
    pad_total = width - visible_len
    left = pad_total // 2
    right = pad_total - left
    return (" " * left) + text + (" " * right)


def compute_kdf_version_suffix(current_version):
    """Return a suffix for display: ' [latest]' or hyperlinked ' [update]'."""
    try:
        info = get_latest_kdf_release_info()
        latest_tag = info.get("tag_name")
        release_url = info.get(
            "html_url",
            "https://github.com/KomodoPlatform/komodo-defi-framework/releases",
        )
        if not latest_tag:
            return " [latest]"
        cv = str(current_version or "").lower()
        lt = str(latest_tag).lower()
        if cv.startswith(lt) or lt in cv:
            return " [latest]"
        return " " + format_hyperlink("[update]", release_url)
    except Exception:
        return " [latest]"


# ---- Seed nodes loader ----

_SEED_NODES_URL = "https://raw.githubusercontent.com/KomodoPlatform/coins/master/seed-nodes.json"
_SEED_NODES_PATH = f"{SCRIPT_PATH}/config/seed-nodes.json"


def get_seednodes_list():
    """Return a list of host values from seed-nodes.json.

    Prefers local config/seed-nodes.json. If missing, attempts to download.
    Returns [] on failure.
    """
    try:
        print(f"Getting seed nodes list from {_SEED_NODES_PATH}...")
        if os.path.exists(_SEED_NODES_PATH):
            with open(_SEED_NODES_PATH, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception as e:
                    os.remove(_SEED_NODES_PATH)
                    return get_seednodes_list()
        else:   
            r = requests.get(_SEED_NODES_URL, timeout=8)
            r.raise_for_status()
            data = r.json()
            os.makedirs(os.path.dirname(_SEED_NODES_PATH), exist_ok=True)
            with open(_SEED_NODES_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        hosts = []
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and entry.get("host"):
                    hosts.append(entry.get("host"))
        return hosts
    except Exception as e:
        print(f"Error getting seed nodes list: {e}")
        print(f"Please update the seed nodes list in your MM2.json file {MM2_JSON_FILE}")
        sys.exit()

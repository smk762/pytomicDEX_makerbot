#!/bin/python3
from lib_const import *


def sec_to_hms(sec):
  minutes, seconds = divmod(sec, 60)
  hours, minutes = divmod(minutes, 60)
  periods = [('h', hours), ('m', minutes), ('s', seconds)]
  return ' '.join('{}{}'.format(int(val), name) for name, val in periods if val)


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
    current_prices = requests.get(PRICES_API).json()
  if '-' in coin:
    coin = coin.split("-")[0]
  if coin in current_prices:
    return float(current_prices[coin]["last_price"])
  else:
    return 0


def download_progress(url, fn):
    with open(fn, 'wb') as f:
        r = requests.get(url, stream=True)
        total = r.headers.get('content-length')

        if total is None:
            f.write(r.content)
        else:
            downloaded = 0
            total = int(total)
            for data in r.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                downloaded += len(data)
                f.write(data)
                done = int(50*downloaded/total)
                sys.stdout.write(f"\rDownloading {fn}: [{'#' * done}{'.' * (50-done)}] {done*2}%")
                sys.stdout.flush()
    sys.stdout.write('\n')
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
    releases_url = f"https://api.github.com/repos/{org}/{repo}/releases/"
    r = requests.get(releases_url)
    try:
        return r.json()
    except:
        error_print(f"{repo} or {org} does not exist!")
        return None


def get_mm2(branch=None):
    assets = get_release_assets_info("komodoplatform", "atomicdex-api")

    for asset in assets:
        if OP_SYS.lower() in asset["browser_download_url"].lower():
            asset_url = asset["browser_download_url"]
            asset_name = asset["name"]
    else:
        error_print("Release not found!")

    if not os.path.exists(asset_name):
        if asset_url:
            download_progress(asset_url, asset_name)
    else:
        status_print(f"{asset_name} already downloaded...")

    with ZipFile(asset_name, 'r') as zf:
        status_print(f'Extracting {asset_name}...')
        zf.extractall()
        if OP_SYS.lower() != 'windows':
            os.chmod('mm2', stat.S_IEXEC)
        status_print('Done!')


def sleep_message(msg, sec):
    status_print(msg)
    time.sleep(sec)

def preexec(): # Don't forward signals.
    os.setpgrp()


def get_order_count(orders):
    maker_orders = {}
    taker_orders = {}
    if 'result' in orders:
        if 'maker_orders' in orders['result']:
            maker_orders = orders['result']['maker_orders']
        if 'taker_orders' in orders['result']:
            taker_orders = orders['result']['taker_orders']
    else:
        error_print(f"Error: {orders}")
    order_count = len(maker_orders) + len(taker_orders)
    return maker_orders, taker_orders, order_count
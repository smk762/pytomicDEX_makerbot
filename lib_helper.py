#!/bin/python3
from lib_const import *

def sec_to_hms(sec):
  minutes, seconds = divmod(sec, 60)
  hours, minutes = divmod(minutes, 60)
  periods = [('h', hours), ('m', minutes), ('s', seconds)]
  return ' '.join('{}{}'.format(int(val), name) for name, val in periods if val)

def get_activate_command(coin):
  return requests.get(f"https://stats.kmd.io/api/atomicdex/activation_commands/?coin={coin}").json()


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
        error_print(f"{repo} or {branch} does not exist!")
        return None


def get_mm2(branch=None):

    if not branch:
        # Get latest release
        assets = get_release_assets_info("komodoplatform", "atomicdex-api")

        for asset in assets:
            if f"{OP_SYS}-Release.zip" in asset["browser_download_url"]:
                asset_url = asset["browser_download_url"]
                asset_name = asset["name"]
        else:
            error_print("Release not found!")

    else:
        status_print(f"WARNING: This will download the latest {branch} build of the AtomicDEX-API (mm2)")
        wait_continue()
        short_hash = get_short_hash("komodoplatform", "atomicdex-api", branch)
        asset_name = f"mm2-{short_hash}-{OP_SYS}-Release.zip"
        asset_url = f"http://195.201.0.6/{branch}/{asset_name}"

    if not os.path.exists(asset_name):
        if asset_url:
            download_progress(asset_url, asset_name)
    else:
        status_print(f"{asset_name} already downloaded...")

    with ZipFile(asset_name, 'r') as zf:
        status_print(f'Extracting {asset_name}...')
        zf.extractall()
        os.chmod('mm2', stat.S_IEXEC)
        status_print('Done!')


#!/usr/bin/env python3
from lib_atomicdex import *


def start_makerbot():
    coins_list = list(set(BUY_COINS + SELL_COINS))
    success_print("Activating Makerbot coins...")
    activate_coins(coins_list)
    # sleep for a bit so in progress orders can be kickstarted
    time.sleep(5)
    command = {
        "userpass": MM2_USERPASS,
        "mmrpc": "2.0",
        "method": "start_simple_market_maker_bot",
        "params": MAKERBOT_PARAMS
    }
    pair_count = len(MAKERBOT_PARAMS["cfg"])
    resp = mm2_proxy(command)
    if 'result' in resp:
        if 'result' in resp['result']:
            if resp['result']['result'] == "Success":
                success_print(f"Makerbot started with {pair_count} pairs")
    else:
        error_print(resp)


def stop_makerbot():
    params = {
        "mmrpc": "2.0",
        "method": "stop_simple_market_maker_bot",
        "params": {},
        "id": 0
    }
    resp = mm2_proxy(params)
    if 'error' in resp:
        if resp['error'].find("bot is already stopped") > 0:
            error_print("The Makerbot is not running")
        else:
            error_print(resp)
    elif 'result' in resp:
        if 'result' in resp['result']:
            if resp['result']['result'] == "Success":
                success_print(f"Makerbot stopped.")
    else:
        error_print(resp)

def update_makerbot():
    view_makerbot_params()
    # Update all or choose a pair
    update_all = True
    if update_all:
        MAKERBOT_SETTINGS = get_makerbot_settings(True)
    # get new settings
    # build new config
    # stop makerbot
    # wait for loop to end (add timer)
    # restart makerbot
    pass


def activate_coins_tui():
    coins_list = color_input("Enter the tickers of coins you want to activate: ").split(" ")
    activate_coins(coins_list)


def view_balances():
    coins_list = get_enabled_coins_list()
    get_balances_table(coins_list)


def view_orders():
    get_orders_table()


def view_swaps():
    get_swaps_summary_table()


def exit_tui():
    q = color_input("Stop AtomicDEX-API on exit? [Y/N]: ")
    while q.lower() not in ["y", "n"]:
        error_print("Invalid option, try again.")
        q = color_input("Stop AtomicDEX-API on exit? [Y/N]: ")

    if q.lower() == "y":
        resp = stop_mm2()
        if 'error' in resp:
            error_print(resp)
        elif "success" in resp:
            status_print("AtomicDEX-API has stopped.")
    sys.exit()



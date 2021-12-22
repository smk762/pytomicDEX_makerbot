#!/usr/bin/env python3
from lib_atomicdex import *


def start_makerbot():
    makerbot_settings = load_makerbot_settings()
    makerbot_params = load_makerbot_params()
    activate_bot_coins()
    view_makerbot_params(makerbot_params)
    # sleep for a bit so in progress orders can be kickstarted
    time.sleep(5)
    command = {
        "userpass": MM2_USERPASS,
        "mmrpc": "2.0",
        "method": "start_simple_market_maker_bot",
        "params": makerbot_params
    }
    pair_count = len(makerbot_params["cfg"])
    resp = mm2_proxy(command)
    if 'result' in resp:
        if 'result' in resp['result']:
            if resp['result']['result'] == "Success":
                success_print(f"Makerbot started with {pair_count} pairs")
            else:
                success_print(resp)
        else:
            success_print(resp)
    elif 'error' in resp:
        if 'error_type' in resp:
            if resp['error_type'] == "AlreadyStarted":
                error_print(f"Makerbot has already been started.")
            else:
                error_print(resp)
        else:
            error_print(resp)
    else:
        error_print(resp)


def stop_makerbot():
    makerbot_settings = load_makerbot_settings()

    params = {
        "mmrpc": "2.0",
        "method": "stop_simple_market_maker_bot",
        "params": {},
        "id": 0
    }
    resp = mm2_proxy(params)
    if 'error' in resp:
        # error_print(resp)
        if 'error_type' in resp:
            if resp['error_type'] == "AlreadyStopping":
                error_print(f"Makerbot is stopping at the end of it's current loop ({makerbot_settings['refresh_rate']} seconds).")
            elif resp['error_type'] == "AlreadyStopped":
                error_print("The Makerbot is not running")
            else:
                error_print(resp)
        else:
            error_print(resp)
    elif 'result' in resp:
        if 'result' in resp['result']:
            if resp['result']['result'] == "Success":
                success_print(f"Makerbot will stop at the end of it's current loop ({makerbot_settings['refresh_rate']} seconds).")
            else:
                success_print(resp)
        else:
            success_print(resp)
    else:
        success_print(resp)
    cancel_all_orders()

def update_makerbot():
    makerbot_params = load_makerbot_params()
    view_makerbot_params(makerbot_params)
 
    # Update all or choose a pair
    q = color_input("Update [A]ll, a [P]air or [R]eturn to menu? [A/P/R] ")

    while q.lower() not in ["a", "p", "r"]:
        error_print("Invalid option, try again.")
        q = color_input("Update [A]ll, a [P]air or [R]eturn to menu? [A/P/R] ")

    if q.lower() == 'a':
        create_makerbot_settings()
    
    elif q.lower() == 'p':
        pair = color_input("Enter the pair you want to update: ")
        while "/" not in pair:
            error_print("Invalid input. Needs to be like SELLTICKER/BASETICKER")
            pair = color_input("Enter the pair you want to update: ")

        pairs = list(makerbot_params['cfg'].keys())

        if pair not in pairs:
            error_print(f"{pair} not found in existing config!")
            q = color_input("[A]dd new pair or [C]ancel? [A/C] ")
            while q.lower() not in ["a", "c"]:
                error_print("Invalid option, try again.")
                q = color_input("[A]dd new pair or [C]ancel? [A/C] ")
            if q.lower() == 'c':
                return
        update_makerbot_pair(pair)
    if q.lower() != "r":
        error_print(f"Note: You need to stop and restart the Makerbot before these settings take effect!")
    # stop makerbot
    # wait for loop to end (add timer)
    # restart makerbot


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



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
    msg = "Update [A]ll, a [P]air, a [C]oin or [R]eturn to menu? [A/P/C/R] "
    valid_options = ["a", "p", "c", "r"]
    q = get_valid_input(msg, valid_options)

    if q.lower() == 'a':
        create_makerbot_settings()

    elif q.lower() == 'c':
        coin = color_input("Enter coin ticker: ")
        msg = "Update coin on [S]ell side, [B]uy side, or [A]ll sides? [S/B/A] "
        valid_options = ["s", "b", "a"]
        q = get_valid_input(msg, valid_options)
        if q.lower() == "s":
            update_makerbot_basepair(coin)
        elif q.lower() == "b":
            update_makerbot_relpair(coin)
        elif q.lower() == "a":
            update_makerbot_basepair(coin)
            update_makerbot_relpair(coin)
    
    elif q.lower() == 'p':
        pair = color_input("Enter the pair you want to update: ")
        while "/" not in pair:
            error_print("Invalid input. Needs to be like SELLTICKER/BASETICKER")
            pair = color_input("Enter the pair you want to update: ")

        pairs = list(makerbot_params['cfg'].keys())

        if pair not in pairs:
            error_print(f"{pair} not found in existing config!")

            msg = "[A]dd new pair or [C]ancel? [A/C] "
            valid_options = ["a", "c"]
            q = get_valid_input(msg, valid_options)

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

def withdraw_funds():
    enabled_coins = get_enabled_coins_list()
    get_balances_table(enabled_coins)
    if len(enabled_coins) > 0:
        coin = color_input("Enter the ticker of the coin you want to withdraw: ")
        while coin not in enabled_coins:
            error_print(f"{coin} is not enabled. Options are |{'|'.join(enabled_coins)}|, try again.")
            coin = color_input("Enter the ticker of the coin you want to withdraw: ")

        amount = color_input(f"Enter the amount of {coin} you want to withdraw, or 'MAX' to withdraw full balance: ")
        amount = validate_withdraw_amount(amount)
        while not amount:
            error_print(f"{amount} is not 'MAX' or a valid numeric value, try again.")
            amount = color_input(f"Enter the amount of {coin} you want to withdraw, or 'MAX' to withdraw full balance: ")    
            amount = validate_withdraw_amount(amount)

        address = color_input(f"Enter the destination address: ")
        while not is_address_valid(coin, address):
            error_print(f"{address} is not a valid {coin} address, try again.")
            address = color_input(f"Enter the destination address: ")
            
        resp = withdraw(coin, amount, address)
        if "error" in resp:
            error_print(resp)
        elif "result" in resp:
            if "tx_hex" in resp["result"]:
                send_resp = send_raw_tx(coin, resp["result"]["tx_hex"])
                if 'tx_hash' in send_resp:
                    success_print(f"{amount} {coin} sent to {address}. TXID: {send_resp['tx_hash']}")
                else:
                    error_print(send_resp)
            else:
                error_print(resp)
        else:
            error_print(resp)


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



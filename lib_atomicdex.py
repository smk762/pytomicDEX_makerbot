#!/usr/bin/env python3
import subprocess
from lib_helper import *


def start_mm2(logfile='mm2_output.log'):
    if not os.path.isfile('mm2'):
        error_print("\nmm2 binary not found in "+SCRIPT_PATH+"!")
        get_mm2("dev")
    mm2_output = open(logfile,'w+')
    subprocess.Popen(["./mm2"], stdout=mm2_output, stderr=mm2_output, universal_newlines=True, preexec_fn=preexec)
    time.sleep(3)
    version = get_version()
    success_print('{:^60}'.format( "AtomicDEX-API starting."))
    success_print('{:^60}'.format( " Use 'tail -f "+logfile+"' for mm2 console messages."))


def mm2_proxy(params):
    params.update({"userpass": MM2_USERPASS})
    #print(json.dumps(params))
    try:
        r = requests.post(MM2_IP, json.dumps(params))
        resp = r.json()
    except requests.exceptions.RequestException as e:
        start_mm2()
        r = requests.post(MM2_IP, json.dumps(params))
        resp = r.json()
        if "error" in resp:
            if resp["error"].find("Userpass is invalid"):
                error_print("MM2 is rejecting your rpc_password. Please check you are not running mm2 or AtomicDEX-Desktop app, and your rpc_password conforms to constraints in https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-setup/configure-mm2-json.html#mm2-json")
                sys.exit()
    return resp


def activate_coins(coins_list):
    for coin in coins_list:
        activated = False
        for protocol in ACTIVATE_COMMANDS:
            if coin in ACTIVATE_COMMANDS[protocol]:
                resp = mm2_proxy(ACTIVATE_COMMANDS[protocol][coin])
                if "result" in resp:
                    status_print(f"{resp['coin']} activated. Balance: {resp['balance']}")
                elif "error" in resp:
                    if resp["error"].find("already initialized") >= 0:
                        status_print(f"{coin} was already activated.")
                    else:
                        error_print(resp)
                activated = True
        if not activated:
            error_print(f"Launch params not found for {coin}!")


# Documentation reference: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-api-legacy/my_recent_swaps.html
def get_swaps_summary_table(limit=500):
    my_recent_swaps = mm2_proxy({"userpass":"$userpass","method":"my_recent_swaps","limit":limit})
    if 'error' in my_recent_swaps:
        error_print(my_recent_swaps['error'])
    elif my_recent_swaps["result"]["total"] == 0:
        status_print("You have no swaps in history!")
    else:
        swaps_summary = {
            'pairs':{},
            'coins':{},
            'totals':{}
        }
        for swap in my_recent_swaps["result"]["swaps"]:
            include_swap = True
            for event in swap["events"]:
                if event["event"]["type"] in ERROR_EVENTS:
                    include_swap = False
                    #print(event["event"]["type"])
                    break
            if include_swap:
                my_coin = swap["my_info"]["my_coin"]
                my_amount = float(swap["my_info"]["my_amount"])
                other_coin = swap["my_info"]["other_coin"]
                other_amount = float(swap["my_info"]["other_amount"])
                pair = f"{my_coin}/{other_coin}"

                if pair not in swaps_summary['pairs']:
                    swaps_summary['pairs'].update({
                        pair:{
                            "swaps":0,
                            "sent":0,
                            "received":0
                        }
                    })
                swaps_summary['pairs'][pair]["swaps"] += 1
                swaps_summary['pairs'][pair]["sent"] += my_amount
                swaps_summary['pairs'][pair]["received"] += other_amount

                for coin in [my_coin, other_coin]:
                    if coin not in swaps_summary['coins']:
                        swaps_summary['coins'].update({
                            coin: {
                                "swaps": 0,
                                "sent": 0,
                                "received": 0
                            }
                        })
                swaps_summary['coins'][my_coin]["sent"] += my_amount
                swaps_summary['coins'][other_coin]["received"] += other_amount
                swaps_summary['coins'][my_coin]["swaps"] += 1
                swaps_summary['coins'][other_coin]["swaps"] += 1
            else:
                #print("skipping, swap failed")
                pass

        current_prices = requests.get(PRICES_API).json()

        total_swaps = 0
        total_value_delta = 0
        # Pairs table
        table_print("-"*96)
        table_print('|{:^30}|{:^8}|{:^16}|{:^16}|{:^20}|'.format(
            "PAIR",
            "SWAPS",
            "SENT",
            "RECEIVED",
            "DELTA"
        ))
        table_print("-"*96)
        for pair in swaps_summary['pairs']:
            base_rel = pair.split("/")
            sent_price = get_price(base_rel[0], current_prices)
            sent_amount = swaps_summary['pairs'][pair]["sent"]
            sent_delta = sent_price * sent_amount
            received_price = get_price(base_rel[1], current_prices)
            received_amount = swaps_summary['pairs'][pair]["received"]
            received_delta = received_price * received_amount
            pair_delta = received_delta - sent_delta
            table_print('|{:^30}|{:^8}|{:^16}|{:^16}|{:^20}|'.format(
                    pair,
                    swaps_summary['pairs'][pair]["swaps"],
                    '{:16.8f}'.format(sent_amount),
                    '{:16.8f}'.format(received_amount),
                    "$"+'{:9.2f}'.format(round(pair_delta,2))+" USD"
                )
            )
            total_swaps += swaps_summary['pairs'][pair]["swaps"]
        table_print("-"*96)
        table_print("")

        # Coins Table
        table_print("-"*108)
        table_print('|{:^12}|{:^8}|{:^16}|{:^16}|{:^16}|{:^16}|{:^16}|'.format(
            "COIN",
            "SWAPS",
            "SENT",
            "RECEIVED",
            "DELTA",
            "PRICE",
            "VALUE DELTA"
        ))
        table_print("-"*108)
        for coin in swaps_summary['coins']:
            delta = swaps_summary['coins'][coin]["received"] - swaps_summary['coins'][coin]["sent"]
            price = get_price(coin, current_prices)
            value_delta = round(price * delta, 2)
            total_value_delta += value_delta
            table_print('|{:^12}|{:^8}|{:^16}|{:^16}|{:^16}|{:^16}|{:^16}|'.format(
                    coin,
                    swaps_summary['coins'][coin]["swaps"],
                    '{:16.8f}'.format(swaps_summary['coins'][coin]["sent"]),
                    '{:16.8f}'.format(swaps_summary['coins'][coin]["received"]),
                    '{:16.8f}'.format(delta),
                    '{:16.8f}'.format(price),
                    "$"+'{:9.2f}'.format(round(value_delta,2))+" USD"
                )
            )
        table_print("-"*108)
        table_print("")

        # Summary
        table_print("-"*42)
        table_print('|{:^40}|\n|{:^40}|'.format(
                f"Total Swaps: {total_swaps}",
                f"Total Delta: USD ${round(total_value_delta, 2)}"
            )
        )
        table_print("-"*42)


# Documentation: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-api-legacy/my_orders.html
def get_orders_table(current_prices=None):
    if not current_prices:
        current_prices = requests.get(PRICES_API).json()
    orders = get_orders()
    maker_orders, taker_orders, order_count = get_order_count(orders)
    if order_count == 0:
        status_print("You have no active orders...")
    else:
        table_print("-"*169)
        table_print('|{:^7}|{:^38}|{:^12}|{:^12}|{:^16}|{:^16}|{:^16}|{:^16}|{:^10}|{:^15}|'.format(
                "Type",
                "UUID",
                "Sell Coin",
                "Buy Coin",
                "Sell Amount",
                "Buy Amount",
                "DEX Price USD",
                "CEX Price USD",
                "% vs CEX",
                "Updated"
            )
        )

        table_print("-"*169)
        output_order_lines("Maker", maker_orders, current_prices)
        output_order_lines("Taker", taker_orders, current_prices)

        table_print("-"*169)
        table_print('{:>152}|{:^15}|'.format(
                "Order count ",
                f"{order_count}"
            )
        )
        table_print('{:>152}{:^16}'.format(
                "",
                "-"*17)
        )


def output_order_lines(ordertype, orders, current_prices=None):
    if not current_prices:
        current_prices = requests.get(PRICES_API).json()
    for uuid in orders:
        sell_coin = orders[uuid]['base']
        buy_coin = orders[uuid]['rel']
        sell_amount = float(orders[uuid]['max_base_vol'])
        sell_price_wrt_rel = float(orders[uuid]['price'])
        buy_amount = sell_amount*sell_price_wrt_rel

        sell_price_cex = get_price(sell_coin, current_prices)
        buy_price_cex = get_price(buy_coin, current_prices)

        cex_price_ratio = sell_price_cex/buy_price_cex 
        pct_vs_cex = round((sell_price_wrt_rel/cex_price_ratio-1)*100,3)
        sell_price_usd = sell_price_cex*(1+pct_vs_cex/100)
        updated = orders[uuid]['updated_at']
        since = sec_to_hms(int(time.time()) - int(updated)/1000) 
        table_print('|{:^7}|{:^38}|{:^12}|{:^12}|{:^16}|{:^16}|{:^16}|{:^16}|{:^10}|{:^15}|'.format(
                ordertype,
                uuid,
                sell_coin,
                buy_coin,
                '{:16.8f}'.format(sell_amount),
                '{:16.8f}'.format(buy_amount),
                '{:10.2f}'.format(sell_price_usd),
                '{:10.2f}'.format(sell_price_cex),
                '{:6.2f}%'.format(pct_vs_cex),
                since
            )
        )


# Documentation: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-api-legacy/my_balance.html
def get_balances_table(coins_list=None, current_prices=None):
    if not coins_list:
        coins_list = get_enabled_coins_list()
    if not current_prices:
        current_prices = requests.get(PRICES_API).json()

    if len(coins_list) == 0:
        status_print("You have no active coins...")
    if len(coins_list) > 0:
        table_print("-"*169)
        table_print('|{:^16s}|{:^24s}|{:^24s}|{:^24s}|{:^58s}|{:^16s}|'.format(
                "Coin",
                "Spendable balance",
                "Unspendable balance",
                "Total balance",
                "Address",
                "USD Value"
            )
        )

        table_print("-"*169)
        total_value = 0
        for coin in coins_list:
            resp = get_balance(coin)
            if 'balance' in resp:
                price = get_price(coin, current_prices)
                total_balance = float(resp['balance']) + float(resp['unspendable_balance'])
                value = round(total_balance * price, 2)
                total_value += value
                table_print('|{:^16s}|{:^24f}|{:^24f}|{:^24f}|{:^58s}|{:^16s}|'.format(
                        coin,
                        float(resp['balance']),
                        float(resp['unspendable_balance']),
                        total_balance,
                        resp['address'],
                        f"${value}"
                    )
                )
            else:
                print(resp)
        table_print("-"*169)
        table_print('{:>151s}|{:^16s}|'.format(
                "Total USD ",
                f"${round(total_value,2)}"
            )
        )
        table_print('{:>151s}{:^16s}'.format(
                "",
                "-"*18)
        )


def view_makerbot_params(makerbot_params):
    table_print("-"*95)
    table_print('|{:^93}|'.format(
            f"MAKERBOT SETTINGS"
        )
    )
    table_print("-"*95)
    table_print('|{:^30}|{:^20}|{:^20}|{:^20}|'.format(
        "PAIR (SELL/BUY)",
        "SPREAD",
        "MIN USD",
        "MAX USD"
    ))
    table_print("-"*95)
    for pair in makerbot_params['cfg']:
        cfg = makerbot_params['cfg'][pair]
        table_print('|{:^30}|{:^20}|{:^20}|{:^20}|'.format(
                pair,
                f'{round((float(cfg["spread"])-1)*100,4)}%',
                f'{cfg["min_volume"]["usd"]}',
                f'{cfg["max_volume"]["usd"]}'
            )
        )
    table_print("-"*95)
    
         


def get_version():
    params = {"method":"version"}
    resp = mm2_proxy(params)
    return resp["result"]


def stop_mm2():
    params = {"method":"stop"}
    resp = mm2_proxy(params)
    return resp


def get_enabled_coins_list():
    params = {"method":"get_enabled_coins"}
    enabled_coins = mm2_proxy(params)
    coins_list = []
    if 'error' in enabled_coins:
        error_print(enabled_coins['error'])
    else:
        for item in enabled_coins["result"]:
            coins_list.append(item["ticker"])
    return coins_list


def update_makerbot_pair(pair):
    base_rel = pair.split("/")
    status_print(f"Updating config to sell {base_rel[0]} for {base_rel[1]}")
    min_usd = color_input("Enter minimum trade value in USD (e.g. 10): ")
    max_usd = color_input("Enter maximum trade value in USD (e.g. 100): ")
    spread = color_input("Enter spread percentage (e.g. 5): ")
    spread = 1+(float(spread)/100)
    reload_makerbot_settings(base_rel[0], base_rel[1])
    update_makerbot_pair_params(base_rel[0], base_rel[1], min_usd, max_usd, spread)
    load_makerbot_params()


def update_makerbot_basepair(coin):
    makerbot_settings = load_makerbot_settings()
    buy_coins = makerbot_settings["buy_coins"]
    status_print(f"Updating config to sell {coin} for {buy_coins}")
    min_usd = color_input("Enter minimum trade value in USD (e.g. 10): ")
    max_usd = color_input("Enter maximum trade value in USD (e.g. 100): ")
    spread = color_input("Enter spread percentage (e.g. 5): ")
    spread = 1+(float(spread)/100)
    reload_makerbot_settings(coin, None)
    update_makerbot_coin_params(coin, "base", min_usd, max_usd, spread)


def update_makerbot_relpair(coin):
    makerbot_settings = load_makerbot_settings()
    sell_coins = makerbot_settings["sell_coins"]
    status_print(f"Updating config to buy {coin} for {sell_coins}")
    min_usd = color_input("Enter minimum trade value in USD (e.g. 10): ")
    max_usd = color_input("Enter maximum trade value in USD (e.g. 100): ")
    spread = color_input("Enter spread percentage (e.g. 5): ")
    spread = 1+(float(spread)/100)
    reload_makerbot_settings(None, coin)
    update_makerbot_coin_params(coin, "rel", min_usd, max_usd, spread)


def reload_makerbot_settings(base=None, rel=None):
    makerbot_settings = load_makerbot_settings()
    if base:
        if base in makerbot_settings["buy_coins"]:
            if rel in makerbot_settings["sell_coins"]:
                return
        else:
            makerbot_settings["buy_coins"].append(base)
    if rel:
        if rel not in makerbot_settings["sell_coins"]:
            makerbot_settings["sell_coins"].append(rel)

    with open("makerbot_settings.json", "w+") as f:
        json.dump(makerbot_settings, f, indent=4)

def activate_bot_coins(enabled_coins=False):
    if not enabled_coins:
        enabled_coins = get_enabled_coins_list()
    makerbot_settings = load_makerbot_settings()
    coins_list = list(set(makerbot_settings["buy_coins"] + makerbot_settings["sell_coins"]) - set(enabled_coins))
    if len(coins_list) > 0:
        success_print("Activating Makerbot coins...")
        activate_coins(coins_list)

def loop_views():
    coins_list = get_enabled_coins_list()
    makerbot_params = load_makerbot_params()
    msg = "\nEnter Ctrl-C to exit\n"
    while True:
        try:
            view_makerbot_params(makerbot_params)
            sleep_message(msg, 20)
            get_balances_table(coins_list)
            sleep_message(msg, 20)
            get_orders_table()
            sleep_message(msg, 20)
            get_swaps_summary_table()
            sleep_message(msg, 20)
        except KeyboardInterrupt:
            break

def get_status():
    enabled_coins = get_enabled_coins_list()
    current_prices = requests.get(PRICES_API).json()
    maker_orders, taker_orders, order_count = get_order_count(get_orders())
    active_swaps_count = len(get_active_swaps()["uuids"])
    successful_swaps_count, failed_swaps_count, delta = get_recent_swaps_info(current_prices)
    balance = get_total_balance_usd(enabled_coins, current_prices)

    status_print('{:^60}\n{:^60}\n{:^60}\n{:^60}'.format(
            f"MM2 Version: {get_version()}",
            f"Swaps: {active_swaps_count} active, {successful_swaps_count} complete, {failed_swaps_count} failed",
            f"Delta: ${round(delta,2)} USD. Balance: ${round(balance,2)} USD",
            f"{(len(enabled_coins))} Coins, {order_count} Orders active.",
        )
    )

def get_total_balance_usd(enabled_coins=None, current_prices=None):
    if not enabled_coins:
        enabled_coins = get_enabled_coins_list()
    if not current_prices:
        current_prices = requests.get(PRICES_API).json()

    total_balance_usd = 0
    for coin in enabled_coins:
        resp = get_balance(coin)
        if 'balance' in resp:
            price = get_price(coin, current_prices)
            coin_balance = float(resp['balance']) + float(resp['unspendable_balance'])
            total_balance_usd += coin_balance
    return round(total_balance_usd,2)



def get_recent_swaps_info(current_prices=None):
    if not current_prices:
        current_prices = requests.get(PRICES_API).json()
        
    total_value_delta = 0
    failed_swaps_count = 0
    successful_swaps_count = 0
    my_recent_swaps = get_recent_swaps()    
    swaps_summary = {"coins":{}}

    for swap in my_recent_swaps["result"]["swaps"]:
        include_swap = True

        for event in swap["events"]:
            if event["event"]["type"] in ERROR_EVENTS:
                include_swap = False
                failed_swaps_count += 1
                break

        if include_swap:
            successful_swaps_count += 1
            my_coin = swap["my_info"]["my_coin"]
            my_amount = float(swap["my_info"]["my_amount"])
            other_coin = swap["my_info"]["other_coin"]
            other_amount = float(swap["my_info"]["other_amount"])

            for coin in [my_coin, other_coin]:
                if coin not in swaps_summary['coins']:
                    swaps_summary['coins'].update({
                        coin: {
                            "sent": 0,
                            "received": 0
                        }
                    })
            swaps_summary['coins'][my_coin]["sent"] += my_amount
            swaps_summary['coins'][other_coin]["received"] += other_amount


    for coin in swaps_summary['coins']:
        delta = swaps_summary['coins'][coin]["received"] - swaps_summary['coins'][coin]["sent"]
        price = get_price(coin, current_prices)
        total_value_delta += round(price * delta, 2)

    return successful_swaps_count, failed_swaps_count, total_value_delta


def get_orders():
    return mm2_proxy({"userpass":"$userpass","method":"my_orders"})

def get_recent_swaps(limit=1000):
    return mm2_proxy({"userpass":"$userpass","method":"my_recent_swaps","limit":limit})

def get_active_swaps():
    return mm2_proxy({"userpass":"$userpass", "method":"active_swaps", "include_status": True})

def cancel_all_orders():
    return mm2_proxy({"userpass":"$userpass","method":"cancel_all_orders","cancel_by":{"type":"All"}})

def get_balance(coin):
    return mm2_proxy({"userpass":"$userpass","method":"my_balance","coin":coin})
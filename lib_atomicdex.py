#!/usr/bin/env python3
import subprocess
from lib_helper import *


def start_mm2(logfile='mm2_output.log'):
    if not os.path.isfile('mm2'):
        error_print("\nmm2 binary not found in "+SCRIPT_PATH+"!")
        get_mm2("dev")
    mm2_output = open(logfile,'w+')
    subprocess.Popen(["./mm2"], stdout=mm2_output, stderr=mm2_output, universal_newlines=True, preexec_fn=preexec)
    
    time.sleep(1)
    version = get_version()
    success_print('{:^60}'.format( "AtomicDEX-API starting."))
    success_print('{:^60}'.format( " Use 'tail -f "+logfile+"' for mm2 console messages."))


def mm2_proxy(params):
    params.update({"userpass": MM2_USERPASS})
    #print(json.dumps(params))
    try:
        r = requests.post(MM2_IP, json.dumps(params))
    except requests.exceptions.RequestException as e:
        start_mm2()
        r = requests.post(MM2_IP, json.dumps(params))
    return r.json()


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
        table_print("-"*57)
        table_print('|{:^12}|{:^8}|{:^16}|{:^16}|'.format(
            "PAIR",
            "SWAPS",
            "SENT",
            "RECEIVED"
        ))
        table_print("-"*57)
        for pair in swaps_summary['pairs']:
            table_print('|{:^12}|{:^8}|{:^16}|{:^16}|'.format(
                    pair,
                    swaps_summary['pairs'][pair]["swaps"],
                    '{:16.8f}'.format(swaps_summary['pairs'][pair]["sent"]),
                    '{:16.8f}'.format(swaps_summary['pairs'][pair]["received"])
                )
            )
            total_swaps += swaps_summary['pairs'][pair]["swaps"]
        table_print("-"*57)
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
                    '{:16.8f}'.format(value_delta),
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
            params = {"userpass":"$userpass","method":"my_balance","coin":coin}
            if len(params) > 0:
                resp = mm2_proxy(params)
                if 'balance' in resp:
                    price = get_price(coin, current_prices)
                    total_balance = float(resp['balance'])+float(resp['unspendable_balance'])
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
            else:
                error_print(f"{coin} is not a recognised coin!")
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
    table_print("-"*85)
    table_print('|{:^83}|'.format(
            f"MAKERBOT SETTINGS"
        )
    )
    table_print("-"*85)
    table_print('|{:^20}|{:^20}|{:^20}|{:^20}|'.format(
        "PAIR",
        "SPREAD",
        "MIN USD",
        "MAX USD"
    ))
    table_print("-"*85)
    for pair in makerbot_params['cfg']:
        cfg = makerbot_params['cfg'][pair]
        table_print('|{:^20}|{:^20}|{:^20}|{:^20}|'.format(
                pair,
                f'{round((float(cfg["spread"])-1)*100,4)}%',
                f'{cfg["min_volume"]["usd"]}',
                f'{cfg["max_volume"]["usd"]}'
            )
        )
    table_print("-"*85)
    
         


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
    update_makerbot_params(base_rel[0], base_rel[1], min_usd, max_usd, spread)
    load_makerbot_params()


def reload_makerbot_settings(base, rel):
    makerbot_settings = load_makerbot_settings()

    if base not in makerbot_settings["buy_coins"]:
        makerbot_settings["buy_coins"].append(base)

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
    
    maker_orders, taker_orders, order_count = get_order_count(get_orders())
    active_swaps_count = len(get_active_swaps()["uuids"])
    successful_swaps_count, failed_swaps_count, delta = get_recent_swaps_info()
    # Add status: order count, swaps in progress, delta
    status_print('{:^60}'.format(
            f"MM2 Version: {get_version()}"
        )
    )
    status_print('{:^60}\n{:^60}'.format(
            f"{(len(get_enabled_coins_list()))} Coins, {order_count} Orders active. Delta: ${round(delta,2)} USD",
            f"Swaps: {active_swaps_count} active, {successful_swaps_count} complete, {failed_swaps_count} failed"
        )
    )

def get_recent_swaps_info():
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

    current_prices = requests.get(PRICES_API).json()

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

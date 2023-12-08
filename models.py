#!/usr/bin/env python3
import os
import sys
import json
import time
import mnemonic
import requests
import pykomodefi
import subprocess
from const import (
    ACTIVE_TASKS,
    USERPASS_FILE,
    PRICES_URL,
    ERROR_EVENTS,
    BOT_PARAMS_FILE,
    BOT_SETTINGS_FILE,
    ACTIVATE_COMMANDS,
    MM2_LOG_FILE,
    MM2BIN,
    MM2_JSON_FILE,
    COINS_LIST
)
from helpers import (
    color_input,
    success_print,
    status_print,
    table_print,
    error_print,
    sleep_message,
    preexec,
    get_mm2,
    get_price,
    get_order_count,
    get_valid_input,
    sec_to_hms,
    generate_rpc_pass,
    get_prices
)


class Dex:
    def __init__(self, mm2_log=MM2_LOG_FILE, mm2_config=MM2_JSON_FILE):
        self.mm2_log = mm2_log
        self.mm2_config = mm2_config
        self.api = pykomodefi.KomoDeFi_API(config=self.mm2_config)

    @property
    def is_running(self):
        try:
            self.api.version
            return True
        except:
            return False

    def start(self):
        if not self.is_running:
            os.environ["MM_CONF_PATH"] = self.mm2_config
            if not os.path.isfile(MM2BIN):
                error_print(f"mm2 binary not found in {MM2BIN}!")
                get_mm2()
            mm2_output = open(self.mm2_log, "w+")
            subprocess.Popen(
                [MM2BIN],
                stdout=mm2_output,
                stderr=mm2_output,
                universal_newlines=True,
                preexec_fn=preexec,
            )
            time.sleep(3)
            success_print("{:^60}".format(" Komodo DeFi Framework starting."))
            success_print(
                "{:^60}".format(
                    f" Use 'tail -f {self.mm2_log}' for mm2 console messages."
                )
            )

    def mm2_proxy(self, params):
        try:
            r = self.api.rpc(params["method"], params)
            resp = r.json()
        except requests.exceptions.RequestException as e:
            self.start()
            r = self.api.rpc(params["method"], params)
            resp = r.json()
            if "error" in resp:
                if resp["error"].find("Userpass is invalid"):
                    error_print(
                        "MM2 is rejecting your rpc_password. Please check you are not running additional instances of mm2 on the same port, and confirm your rpc_password conforms to constraints in https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-setup/configure-mm2-json.html#mm2-json"
                    )
                    sys.exit()
        return resp

    def activate_coins(self, coins_list):
        for coin in coins_list:
            if coin == "TKL":
                coin = "TOKEL"
            activation_params = self.get_activation_command(coin)
            if activation_params:
                resp = self.mm2_proxy(activation_params)
                if "result" in resp:
                    if "balance" in resp["result"]:
                        status_print(f"{coin} activated. Balance: {resp['balance']}")
                    elif "task_id" in resp["result"]:
                        status_print(
                            f"{coin} activated. Task ID: {resp['result']['task_id']}"
                        )
                        if coin in ["ARRR", "ZOMBIE"]:
                            ACTIVE_TASKS.update(
                                {
                                    "task::enable_z_coin::status": resp["result"][
                                        "task_id"
                                    ]
                                }
                            )
                        else:
                            ACTIVE_TASKS.update({"unknown": resp["result"]["task_id"]})
                    else:
                        status_print(
                            f"{coin} is activating. Response: {resp['result']}"
                        )
                elif "error" in resp:
                    if resp["error"].find("already initialized") >= 0:
                        status_print(f"{coin} was already activated.")
                    else:
                        error_print(resp)
            else:
                error_print(f"Launch params not found for {coin}!")

    def get_activation_command(self, coin):
        activation_command = None
        for protocol in ACTIVATE_COMMANDS:
            if coin in ACTIVATE_COMMANDS[protocol]:
                activation_command = ACTIVATE_COMMANDS[protocol][coin]
        return activation_command

    def get_task(self, method, task_id):
        params = {
            "method": method,
            "mmrpc": "2.0",
            "params": {"task_id": task_id, "forget_if_finished": False},
        }
        resp = self.mm2_proxy(params)
        return resp

    def get_version(self):
        return self.api.version

    def quit(self):
        resp = self.mm2_proxy({"method": "stop"})
        return resp

    @property
    def enabled_coins_list(self):
        try:
            return [i["ticker"] for i in self.api.enabled_coins]
        except Exception as e:
            print(e)
            return []

    @property
    def status(self):
        enabled_coins = self.enabled_coins_list
        current_prices = get_prices()
        maker_orders, taker_orders, order_count = get_order_count(self.api.orders)
        successful_swaps_count, failed_swaps_count, delta = self.get_recent_swaps_info(
            current_prices
        )
        active_swaps_count = len(self.api.active_swaps["uuids"])
        balance = self.get_total_balance_usd(enabled_coins, current_prices)

        return "{:^60}\n{:^60}\n{:^60}\n{:^60}".format(
            f"MM2 Version: {self.api.version}",
            f"Swaps: {active_swaps_count} active, {successful_swaps_count} complete, {failed_swaps_count} failed",
            f"Delta: ${round(delta,2)} USD. Balance: ${round(balance,2)} USD",
            f"{(len(enabled_coins))} Coins, {order_count} Orders active.",
        )

    def get_total_balance_usd(self, enabled_coins=None, current_prices=None):
        if not enabled_coins:
            enabled_coins = self.enabled_coins_list
        if not current_prices:
            current_prices = get_prices()

        total_balance_usd = 0
        for coin in enabled_coins:
            resp = self.get_balance(coin)
            if "balance" in resp:
                price = get_price(coin, current_prices)
                coin_balance = float(resp["balance"]) + float(
                    resp["unspendable_balance"]
                )
                total_balance_usd += coin_balance * price
        return round(total_balance_usd, 2)

    def get_recent_swaps_info(self, current_prices=None):
        if not current_prices:
            current_prices = get_prices()

        total_value_delta = 0
        failed_swaps_count = 0
        successful_swaps_count = 0
        recent_swaps = self.get_recent_swaps()
        swaps_summary = {"coins": {}}

        for swap in recent_swaps["result"]["swaps"]:
            include_swap = True

            for event in swap["events"]:
                if event["event"]["type"] in ERROR_EVENTS:
                    include_swap = False
                    failed_swaps_count += 1
                    break

            if include_swap:
                for event in swap["events"]:
                    if event["event"]["type"] == "Finished":
                        successful_swaps_count += 1
                my_coin = swap["my_info"]["my_coin"]
                my_amount = float(swap["my_info"]["my_amount"])
                other_coin = swap["my_info"]["other_coin"]
                other_amount = float(swap["my_info"]["other_amount"])

                for coin in [my_coin, other_coin]:
                    if coin not in swaps_summary["coins"]:
                        swaps_summary["coins"].update(
                            {coin: {"sent": 0, "received": 0}}
                        )
                swaps_summary["coins"][my_coin]["sent"] += my_amount
                swaps_summary["coins"][other_coin]["received"] += other_amount

        for coin in swaps_summary["coins"]:
            delta = (
                swaps_summary["coins"][coin]["received"]
                - swaps_summary["coins"][coin]["sent"]
            )
            price = get_price(coin, current_prices)
            total_value_delta += round(price * delta, 2)

        return successful_swaps_count, failed_swaps_count, total_value_delta

    # https://developers.komodoplatform.com/basic-docs/atomicdex-api-legacy/my_recent_swaps.html
    def get_recent_swaps(self, limit=1000):
        return self.mm2_proxy({"method": "my_recent_swaps", "limit": limit})

    # https://developers.komodoplatform.com/basic-docs/atomicdex-api-legacy/cancel_all_orders.html
    def cancel_all_orders(self, coin=None):
        if coin:
            params = {
                "method": "cancel_all_orders",
                "cancel_by": {"type": "Coin", "data": {"ticker": coin}},
            }
            return self.mm2_proxy(params)
        params = {"method": "cancel_all_orders", "cancel_by": {"type": "All"}}
        return self.mm2_proxy(params)

    # https://developers.komodoplatform.com/basic-docs/atomicdex-api-legacy/my_balance.html
    def get_balance(self, coin):
        return self.mm2_proxy({"method": "my_balance", "coin": coin})

    # https://developers.komodoplatform.com/basic-docs/atomicdex-api-legacy/my_balance.html
    def disable_coin(self, coin):
        return self.mm2_proxy({"method": "disable_coin", "coin": coin})

    # https://developers.komodoplatform.com/basic-docs/atomicdex-api-20/withdraw.html
    def withdraw(self, coin, amount, address):
        if amount == "MAX":
            return self.mm2_proxy(
                {
                    "mmrpc": "2.0",
                    "method": "withdraw",
                    "params": {"coin": coin, "to": address, "max": True},
                    "id": 0,
                }
            )
        else:
            return self.mm2_proxy(
                {
                    "mmrpc": "2.0",
                    "method": "withdraw",
                    "params": {"coin": coin, "to": address, "amount": amount},
                    "id": 0,
                }
            )

    # https://developers.komodoplatform.com/basic-docs/atomicdex-api-legacy/send_raw_transaction.html
    def send_raw_tx(self, coin, tx_hex):
        return self.mm2_proxy(
            {"method": "send_raw_transaction", "coin": coin, "tx_hex": tx_hex}
        )

    # https://developers.komodoplatform.com/basic-docs/atomicdex-api-legacy/validateaddress.html
    def validate_address(self, coin, address):
        return self.mm2_proxy(
            {"method": "validateaddress", "coin": coin, "address": address}
        )

    # https://developers.komodoplatform.com/basic-docs/atomicdex-api-legacy/validateaddress.html
    def is_address_valid(self, coin, address):
        return self.validate_address(coin, address)["result"]["is_valid"]

    def validate_withdraw_amount(self, amount):
        if amount in ["MAX", "max"]:
            return "MAX"
        else:
            try:
                return float(amount)
            except:
                return False


class MakerBot:
    def __init__(self, mm2_config=MM2_JSON_FILE):
        self.config = Config()
        self.dex = Dex(mm2_config=mm2_config)
        self.params = self.config.load_params()
        self.settings = self.config.load_settings()
        pass

    def activate_bot_coins(self, enabled_coins=False):
        if not enabled_coins:
            enabled_coins = self.dex.enabled_coins_list
        coins_list = list(
            set(self.settings["buy_coins"] + self.settings["sell_coins"])
            - set(enabled_coins)
        )
        if len(coins_list) > 0:
            success_print("Activating Makerbot coins...")
            self.dex.activate_coins(coins_list)
            success_print(f"Done. Active coins: {self.dex.enabled_coins_list}")

    def start(self):
        self.activate_bot_coins(self.dex.enabled_coins_list)
        # sleep for a bit so in progress orders can be kickstarted
        time.sleep(5)
        pair_count = len(self.params["cfg"])
        resp = self.dex.api.rpc(
            "start_simple_market_maker_bot", self.params, v2=True
        ).json()
        if "result" in resp:
            if "result" in resp["result"]:
                if resp["result"]["result"] == "Success":
                    success_print(f"Makerbot started with {pair_count} pairs")
                else:
                    success_print(resp)
            else:
                success_print(resp)
        elif "error" in resp:
            if "error_type" in resp:
                if resp["error_type"] == "AlreadyStarted":
                    error_print(f"Makerbot has already been started.")
                else:
                    error_print(resp)
            else:
                error_print(resp)
        else:
            error_print(resp)

    def stop(self):
        params = {
            "mmrpc": "2.0",
            "method": "stop_simple_market_maker_bot",
            "params": {},
            "id": 0,
        }
        resp = self.dex.mm2_proxy(params)
        if "error" in resp:
            # error_print(resp)
            if "error_type" in resp:
                if resp["error_type"] == "AlreadyStopping":
                    error_print(
                        f"Makerbot is stopping at the end of it's current loop ({self.settings['refresh_rate']} seconds)."
                    )
                elif resp["error_type"] == "AlreadyStopped":
                    error_print("The Makerbot is not running")
                else:
                    error_print(resp)
            else:
                error_print(resp)
        elif "result" in resp:
            if "result" in resp["result"]:
                if resp["result"]["result"] == "Success":
                    success_print(
                        f"Makerbot will stop at the end of it's current loop ({self.settings['refresh_rate']} seconds)."
                    )
                else:
                    success_print(resp)
            else:
                success_print(resp)
        else:
            success_print(resp)
        self.dex.cancel_all_orders()

    def reset_config(self):
        self.config.init_bot_params(True)

    def update(self):
        # Update all or choose a pair
        msg = "Update [A]ll, a [P]air, a [C]oin or [R]eturn to menu? [A/P/C/R] "
        valid_options = ["a", "p", "c", "r"]
        q = get_valid_input(msg, valid_options)

        if q.lower() == "a":
            self.config.create_bot_settings()

        elif q.lower() == "c":
            coin = color_input("Enter coin ticker: ")
            msg = "Update coin on [S]ell side, [B]uy side, or [A]ll sides? [S/B/A] "
            valid_options = ["s", "b", "a"]
            q = get_valid_input(msg, valid_options)
            if q.lower() == "s":
                self.config.update_basepair(coin)
            elif q.lower() == "b":
                self.config.update_relpair(coin)
            elif q.lower() == "a":
                self.config.update_basepair(coin)
                self.config.update_relpair(coin)

        elif q.lower() == "p":
            pair = color_input("Enter the pair you want to update: ")
            while "/" not in pair:
                error_print("Invalid input. Needs to be like SELLTICKER/BASETICKER")
                pair = color_input("Enter the pair you want to update: ")

            pairs = list(self.params["cfg"].keys())

            if pair not in pairs:
                error_print(f"{pair} not found in existing config!")

                msg = "[A]dd new pair or [C]ancel? [A/C] "
                valid_options = ["a", "c"]
                q = get_valid_input(msg, valid_options)

                if q.lower() == "c":
                    return

            self.config.update_makerbot_pair(pair)
        if q.lower() != "r":
            error_print(
                f"Note: You need to stop and restart the Makerbot before these settings take effect!"
            )
        # stop makerbot
        # wait for loop to end (add timer)
        # restart makerbot


class Table:
    def __init__(self):
        self.config = Config()
        self.dex = Dex()

    def swaps_summary(self, recent_swaps, limit=500):
        if "error" in recent_swaps:
            error_print(recent_swaps["error"])
        elif recent_swaps["result"]["total"] == 0:
            status_print("You have no swaps in history!")
        else:
            summary = {"pairs": {}, "coins": {}, "totals": {}}
            for swap in recent_swaps["result"]["swaps"]:
                include_swap = True
                for event in swap["events"]:
                    if event["event"]["type"] in ERROR_EVENTS:
                        include_swap = False
                        # print(event["event"]["type"])
                        break
                if include_swap:
                    my_coin = swap["my_info"]["my_coin"]
                    my_amount = float(swap["my_info"]["my_amount"])
                    other_coin = swap["my_info"]["other_coin"]
                    other_amount = float(swap["my_info"]["other_amount"])
                    pair = f"{my_coin}/{other_coin}"

                    if pair not in summary["pairs"]:
                        summary["pairs"].update(
                            {pair: {"swaps": 0, "sent": 0, "received": 0}}
                        )
                    summary["pairs"][pair]["swaps"] += 1
                    summary["pairs"][pair]["sent"] += my_amount
                    summary["pairs"][pair]["received"] += other_amount

                    for coin in [my_coin, other_coin]:
                        if coin not in summary["coins"]:
                            summary["coins"].update(
                                {coin: {"swaps": 0, "sent": 0, "received": 0}}
                            )
                    summary["coins"][my_coin]["sent"] += my_amount
                    summary["coins"][other_coin]["received"] += other_amount
                    summary["coins"][my_coin]["swaps"] += 1
                    summary["coins"][other_coin]["swaps"] += 1
                else:
                    # print("skipping, swap failed")
                    pass

            current_prices = get_prices()

            total_swaps = 0
            total_value_delta = 0
            # Pairs table
            table_print("-" * 96)
            table_print(
                "|{:^30}|{:^8}|{:^16}|{:^16}|{:^20}|".format(
                    "PAIR", "SWAPS", "SENT", "RECEIVED", "DELTA"
                )
            )
            table_print("-" * 96)
            for pair in summary["pairs"]:
                base_rel = pair.split("/")
                sent_price = get_price(base_rel[0], current_prices)
                sent_amount = summary["pairs"][pair]["sent"]
                sent_delta = sent_price * sent_amount
                received_price = get_price(base_rel[1], current_prices)
                received_amount = summary["pairs"][pair]["received"]
                received_delta = received_price * received_amount
                pair_delta = received_delta - sent_delta
                table_print(
                    "|{:^30}|{:^8}|{:^16}|{:^16}|{:^20}|".format(
                        pair,
                        summary["pairs"][pair]["swaps"],
                        "{:16.8f}".format(sent_amount),
                        "{:16.8f}".format(received_amount),
                        "$" + "{:9.2f}".format(round(pair_delta, 2)) + " USD",
                    )
                )
                total_swaps += summary["pairs"][pair]["swaps"]
            table_print("-" * 96)
            table_print("")

            # Coins Table
            table_print("-" * 108)
            table_print(
                "|{:^12}|{:^8}|{:^16}|{:^16}|{:^16}|{:^16}|{:^16}|".format(
                    "COIN", "SWAPS", "SENT", "RECEIVED", "DELTA", "PRICE", "VALUE DELTA"
                )
            )
            table_print("-" * 108)
            for coin in summary["coins"]:
                delta = (
                    summary["coins"][coin]["received"] - summary["coins"][coin]["sent"]
                )
                price = get_price(coin, current_prices)
                value_delta = round(price * delta, 2)
                total_value_delta += value_delta
                table_print(
                    "|{:^12}|{:^8}|{:^16}|{:^16}|{:^16}|{:^16}|{:^16}|".format(
                        coin,
                        summary["coins"][coin]["swaps"],
                        "{:16.8f}".format(summary["coins"][coin]["sent"]),
                        "{:16.8f}".format(summary["coins"][coin]["received"]),
                        "{:16.8f}".format(delta),
                        "{:16.8f}".format(price),
                        "$" + "{:9.2f}".format(round(value_delta, 2)) + " USD",
                    )
                )
            table_print("-" * 108)
            table_print("")

            # Summary
            table_print("-" * 42)
            table_print(
                "|{:^40}|\n|{:^40}|".format(
                    f"Total Swaps: {total_swaps}",
                    f"Total Delta: USD ${round(total_value_delta, 2)}",
                )
            )
            table_print("-" * 42)

    # Documentation: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-api-legacy/my_orders.html
    def orders(self, orders_data, current_prices=None):
        if not current_prices:
            current_prices = get_prices()
        maker_orders, taker_orders, order_count = get_order_count(orders_data)
        if order_count == 0:
            status_print("You have no active orders...")
        else:
            table_print("-" * 169)
            table_print(
                "|{:^7}|{:^38}|{:^12}|{:^12}|{:^16}|{:^16}|{:^16}|{:^16}|{:^10}|{:^15}|".format(
                    "Type",
                    "UUID",
                    "Sell Coin",
                    "Buy Coin",
                    "Sell Amount",
                    "Buy Amount",
                    "DEX Price USD",
                    "CEX Price USD",
                    "% vs CEX",
                    "Updated",
                )
            )

            table_print("-" * 169)
            self.output_order_lines("Maker", maker_orders, current_prices)
            self.output_order_lines("Taker", taker_orders, current_prices)

            table_print("-" * 169)
            table_print("{:>152}|{:^15}|".format("Order count ", f"{order_count}"))
            table_print("{:>152}{:^16}".format("", "-" * 17))

    def output_order_lines(self, ordertype, orders, current_prices=None):
        if not current_prices:
            current_prices = get_prices()
        for uuid in orders:
            sell_coin = orders[uuid]["base"]
            buy_coin = orders[uuid]["rel"]
            sell_amount = float(orders[uuid]["max_base_vol"])
            sell_price_wrt_rel = float(orders[uuid]["price"])
            buy_amount = sell_amount * sell_price_wrt_rel

            sell_price_cex = get_price(sell_coin, current_prices)
            buy_price_cex = get_price(buy_coin, current_prices)

            if sell_price_cex == 0:
                self.dex.cancel_all_orders(sell_coin)

            elif buy_price_cex == 0:
                self.dex.cancel_all_orders(buy_coin)

            else:
                cex_price_ratio = sell_price_cex / buy_price_cex
                pct_vs_cex = round((sell_price_wrt_rel / cex_price_ratio - 1) * 100, 3)
                sell_price_usd = sell_price_cex * (1 + pct_vs_cex / 100)
                updated = orders[uuid]["updated_at"]
                since = sec_to_hms(int(time.time()) - int(updated) / 1000)
                table_print(
                    "|{:^7}|{:^38}|{:^12}|{:^12}|{:^16}|{:^16}|{:^16}|{:^16}|{:^10}|{:^15}|".format(
                        ordertype,
                        uuid,
                        sell_coin,
                        buy_coin,
                        "{:16.8f}".format(sell_amount),
                        "{:16.8f}".format(buy_amount),
                        "{:10.2f}".format(sell_price_usd),
                        "{:10.2f}".format(sell_price_cex),
                        "{:6.2f}%".format(pct_vs_cex),
                        since,
                    )
                )

    # Documentation: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-api-legacy/my_balance.html
    def balances(self, coins_list, current_prices=None):
        if not current_prices:
            current_prices = get_prices()

        if len(coins_list) == 0:
            status_print("You have no active coins...")
        if len(coins_list) > 0:
            table_print("-" * 169)
            table_print(
                "|{:^16s}|{:^24s}|{:^24s}|{:^24s}|{:^58s}|{:^16s}|".format(
                    "Coin",
                    "Spendable balance",
                    "Unspendable balance",
                    "Total balance",
                    "Address",
                    "USD Value",
                )
            )

            table_print("-" * 169)
            total_value = 0
            for coin in coins_list:
                resp = Dex().get_balance(coin)
                if "balance" in resp:
                    price = get_price(coin, current_prices)
                    total_balance = float(resp["balance"]) + float(
                        resp["unspendable_balance"]
                    )
                    value = round(total_balance * price, 2)
                    total_value += value
                    table_print(
                        "|{:^16s}|{:^24f}|{:^24f}|{:^24f}|{:^58s}|{:^16s}|".format(
                            coin,
                            float(resp["balance"]),
                            float(resp["unspendable_balance"]),
                            total_balance,
                            resp["address"],
                            f"${value:.2f}",
                        )
                    )
                else:
                    print(resp)
            table_print("-" * 169)
            table_print(
                "{:>151s}|{:^16s}|".format("Total USD ", f"${round(total_value,2)}")
            )
            table_print("{:>151s}{:^16s}".format("", "-" * 18))

    def bot_params(self, params):
        table_print("-" * 95)
        table_print("|{:^93}|".format(f"MAKERBOT SETTINGS"))
        table_print("-" * 95)
        table_print(
            "|{:^30}|{:^20}|{:^20}|{:^20}|".format(
                "PAIR (SELL/BUY)", "SPREAD", "MIN USD", "MAX USD"
            )
        )
        table_print("-" * 95)
        for pair in params["cfg"]:
            cfg = params["cfg"][pair]
            table_print(
                "|{:^30}|{:^20}|{:^20}|{:^20}|".format(
                    pair,
                    f'{round((float(cfg["spread"])-1)*100,4)}%',
                    f'{cfg["min_volume"]["usd"]}',
                    f'{cfg["max_volume"]["usd"]}',
                )
            )
        table_print("-" * 95)

    def loop_views(self):
        msg = "\nEnter Ctrl-C to exit\n"
        while True:
            try:
                self.bot_params(self.config.load_params())
                coins_list = Dex().enabled_coins_list
                sleep_message(msg, 10)
                self.balances(coins_list)
                sleep_message(msg, 10)
                self.orders(Dex().api.orders)
                sleep_message(msg, 10)
                self.swaps_summary(Dex().api.rpc("my_recent_swaps").json())
                sleep_message(msg, 10)
            except KeyboardInterrupt:
                break


class Config:
    def __init__(self):
        pass

    # Documentation reference: https://developers.komodoplatform.com/basic-docs/atomicdex-api-20-dev/start_simple_market_maker_bot.html
    def load_params(self):
        try:
            with open(BOT_PARAMS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def load_settings(self):
        try:
            with open(BOT_SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def create_bot_params(self, bot_settings):
        buy_coins = bot_settings["buy_coins"]
        sell_coins = bot_settings["sell_coins"]
        min_usd = bot_settings["default_min_usd"]
        max_usd = bot_settings["default_max_usd"]
        spread = bot_settings["default_spread"]
        order_refresh_rate = bot_settings["refresh_rate"]
        use_bidirectional_threshold = True
        params = {"price_url": PRICES_URL, "bot_refresh_rate": int(order_refresh_rate)}

        configs = {}
        for base in sell_coins:
            for rel in buy_coins:
                if base != rel:
                    configs.update(
                        {
                            f"{base}/{rel}": self.get_config(
                                base, rel, min_usd, max_usd, spread
                            )
                        }
                    )

        params.update({"cfg": configs})

        with open(BOT_PARAMS_FILE, "w", encoding="utf-8") as f:
            json.dump(params, f, ensure_ascii=False, indent=4)

    def init_bot_params(self, reset=False):
        if not os.path.exists(BOT_PARAMS_FILE) or reset:
            self.create_bot_settings()

    def create_bot_settings(self):
        q = "n"
        while q.lower() == "n":
            sell_coins = self.validate_list_input(
                "Enter tickers of coins you want to sell, seperated by a space (default: KMD LTC):\n",
                ["KMD", "LTC"],
                set(COINS_LIST),
                "tickers",
                2
            )
            buy_coins = self.validate_list_input(
                "Enter tickers of coins you want to buy, seperated by a space (press enter to use same coins as above):\n",
                sell_coins,
                set(COINS_LIST),                
                "tickers",
                2
            )
            min_usd = self.validate_float_input(
                "Enter default minimum trade value in USD (default: $10): ",
                10,
                1
            )
            max_usd = self.validate_float_input(
                "Enter default maximum trade value in USD (default: $500): ",
                500,
                20
            )
            spread = self.validate_float_input(
                "Enter default spread percentage (default: 3%): ",
                3,
                0.01
            )
            refresh_rate = self.validate_int_input(
                "How often to update prices in minutes (default: 3): ",
                3,
                2
            ) * 60

            bot_settings = {
                "sell_coins": list(set(sell_coins)),
                "buy_coins": list(set(buy_coins)),
                "default_min_usd": int(min_usd),
                "default_max_usd": int(max_usd),
                "default_spread": 1 + (float(spread) / 100),
                "refresh_rate": refresh_rate,
                "prices_api": PRICES_URL,
                "prices_api_timeout": 180,
                "use_bidirectional_threshold": True,
            }

            table_print(json.dumps(bot_settings, indent=4))
            q = color_input("Confirm configuration? [Y/N]: ")

            while q.lower() not in ["y", "n"]:
                error_print("Invalid option!")
                q = color_input("Confirm configuration? [Y/N]: ")

        with open(BOT_SETTINGS_FILE, "w+") as f:
            json.dump(bot_settings, f, indent=4)
        self.create_bot_params(bot_settings)

    def get_bot_settings(self):
        if not os.path.exists(BOT_SETTINGS_FILE):
            status_print("\nFirst we need to set up some configs...")
            status_print(
                "\nDon't forget to evaluate your risk tolerance and only trade small amounts you are comfortable with."
            )
            self.create_bot_settings()

    # Load or Create MM2.json
    # Documentation: https://developers.komodoplatform.com/basic-docs/atomicdex/atomicdex-setup/configure-mm2-json.html#mm2-json
    def init_MM2_json(self):
        if not os.path.exists(MM2_JSON_FILE):
            table_print(
                "Looks like you dont have an MM2.json file, lets create one now..."
            )
            rpc_password = generate_rpc_pass(16)
            mm2_conf = {
                "gui": "pyMakerbot",
                "netid": 8762,
                "rpcport": 7763,
                "i_am_seed": False,
                "rpc_password": rpc_password,
                "userhome": '/${HOME#"/"}',
            }

            new_seed = color_input("[E]nter seed manually or [G]enerate one? [E/G]: ")
            while new_seed not in ["G", "g", "E", "e"]:
                error_print("Invalid input!")
                new_seed = color_input(
                    "[E]nter seed manually or [G]enerate one? [E/G]: "
                )

            if new_seed in ["E", "e"]:
                passphrase = color_input("Enter a seed phrase: ")
            else:
                m = mnemonic.Mnemonic("english")
                passphrase = m.generate(strength=256)

            mm2_conf.update({"passphrase": passphrase})

            with open(MM2_JSON_FILE, "w+") as f:
                json.dump(mm2_conf, f, indent=4)
                status_print(f"{MM2_JSON_FILE} file created.")
                status_print(
                    "Be sure to make a secure backup of your seed phrase offline!"
                )

            with open(USERPASS_FILE, "w+") as f:
                f.write(f'userpass="{rpc_password}"')
                status_print("userpass file created.")

    def get_config(self, base, rel, min_usd, max_usd, spread):
        config_template = {
            "base": "base_coin",
            "rel": "rel_coin",
            "base_confs": 3,
            "base_nota": True,
            "rel_confs": 3,
            "rel_nota": True,
            "enable": True,
            "price_elapsed_validity": 180,
            "check_last_bidirectional_trade_thresh_hold": True,
        }
        cfg = config_template.copy()
        cfg.update(
            {
                "base": base,
                "rel": rel,
                "min_volume": {"usd": float(min_usd)},
                "max_volume": {"usd": float(max_usd)},
                "spread": round(spread, 4),
            }
        )
        return cfg

    def update_pair_params(self, base, rel, min_usd, max_usd, spread):
        bot_params = self.load_params()
        config = self.get_config(base, rel, min_usd, max_usd, spread)
        bot_params["cfg"].update({f"{base}/{rel}": config})

        with open(BOT_PARAMS_FILE, "w", encoding="utf-8") as f:
            json.dump(bot_params, f, ensure_ascii=False, indent=4)

    def update_makerbot_coin_params(self, coin, side, min_usd, max_usd, spread):
        bot_settings = self.load_settings()
        bot_params = self.load_params()

        if side == "base":
            base = coin
            for rel in bot_settings["buy_coins"]:
                if base != rel:
                    config = self.get_config(base, rel, min_usd, max_usd, spread)
                    bot_params["cfg"].update({f"{base}/{rel}": config})

        elif side == "rel":
            rel = coin
            for base in bot_settings["sell_coins"]:
                if base != rel:
                    config = self.get_config(base, rel, min_usd, max_usd, spread)
                    bot_params["cfg"].update({f"{base}/{rel}": config})

        with open(BOT_PARAMS_FILE, "w", encoding="utf-8") as f:
            json.dump(bot_params, f, ensure_ascii=False, indent=4)

    def update_makerbot_pair(self, pair):
        base_rel = pair.split("/")
        status_print(f"Updating config to sell {base_rel[0]} for {base_rel[1]}")
        min_usd = color_input("Enter minimum trade value in USD (e.g. 10): ")
        max_usd = color_input("Enter maximum trade value in USD (e.g. 100): ")
        spread = color_input("Enter spread percentage (e.g. 5): ")
        spread = 1 + (float(spread) / 100)
        self.reload_settings(base_rel[0], base_rel[1])
        self.update_pair_params(base_rel[0], base_rel[1], min_usd, max_usd, spread)
        self.load_params()

    def update_basepair(self, coin):
        bot_settings = self.load_settings()
        buy_coins = bot_settings["buy_coins"]
        status_print(f"Updating config to sell {coin} for {buy_coins}")
        min_usd = color_input("Enter minimum trade value in USD (e.g. 10): ")
        max_usd = color_input("Enter maximum trade value in USD (e.g. 100): ")
        spread = color_input("Enter spread percentage (e.g. 5): ")
        spread = 1 + (float(spread) / 100)
        self.reload_settings(coin, None)
        self.update_makerbot_coin_params(coin, "base", min_usd, max_usd, spread)

    def update_relpair(self, coin):
        bot_settings = self.load_settings()
        sell_coins = bot_settings["sell_coins"]
        status_print(f"Updating config to buy {coin} for {sell_coins}")
        min_usd = color_input("Enter minimum trade value in USD (e.g. 10): ")
        max_usd = color_input("Enter maximum trade value in USD (e.g. 100): ")
        spread = color_input("Enter spread percentage (e.g. 5): ")
        spread = 1 + (float(spread) / 100)
        self.reload_settings(None, coin)
        self.update_makerbot_coin_params(coin, "rel", min_usd, max_usd, spread)

    def reload_settings(self, base=None, rel=None):
        bot_settings = self.load_settings()
        if base and rel:
            if base not in bot_settings["buy_coins"]:
                bot_settings["buy_coins"].append(base)
            if rel not in bot_settings["sell_coins"]:
                bot_settings["sell_coins"].append(rel)
        elif base:
            if base not in bot_settings["buy_coins"]:
                bot_settings["buy_coins"].append(base)
        elif rel:
            if rel not in bot_settings["sell_coins"]:
                bot_settings["sell_coins"].append(rel)

        with open(BOT_SETTINGS_FILE, "w+") as f:
            json.dump(bot_settings, f, indent=4)

    def validate_float_input(self, q=None, default=0, min=0):
        while True:
            try:
                if q is None:
                    value = default
                else:
                    value = color_input(q).replace("$", "").replace("%", "")
                    if value == "":
                        value = default
                value = float(value)
                if value < min:
                    raise ValueError
                return float(value)
            except ValueError:
                error_print(f"Value must be > {min}!")
            except TypeError:
                error_print("Value must be numeric!")
            except KeyboardInterrupt:
                if value is None:
                    value = default
                elif value == "":
                    value = default
                return value
            

    def validate_int_input(self, q=None, default=0, min=0):
        while True:
            try:
                if q is None:
                    value = default
                else:
                    value = color_input(q).replace("$", "").replace("%", "")
                    if value == "":
                        value = default
                value = int(value)
                if value < min:
                    raise ValueError
                return int(value)
            except ValueError:
                error_print(f"Value must be > {min}!")
            except TypeError:
                error_print("Value must be numeric!")
            except KeyboardInterrupt:
                if value is None:
                    value = default
                elif value == "":
                    value = default
                return value

    def validate_list_input(self, q=None, default=list(), valid_options=set(), category=None, min_length=2):
        while True:
            try:
                if q is None:
                    value = default
                else:
                    value = color_input(q).split(" ")
                    if value[0] == "":
                        value = default
                value = [i for i in value if i != '']
                if len(value) < min_length:
                    raise IndexError
                if len(valid_options) > 0:
                    invalid_options = set(value) - valid_options
                    if len(invalid_options) != 0:
                        raise ValueError
                return value
            except ValueError:
                error_print(f"The following selections are not a valid option: {invalid_options}, try again.")
                if category == "tickers":
                    error_print("The valid tickers can be found at https://github.com/KomodoPlatform/coins/blob/master/utils/coins_config.json")
            except IndexError:
                error_print("You must select two or more tickers, try again")            
            except KeyboardInterrupt:
                if value is None:
                    value = default
                elif value[0] == "":
                    value = default
                return value


table = Table()
dex = Dex()


class Tui:
    def __init__(self):
        self.config = Config()
        self.config.init_MM2_json()
        self.config.init_bot_params()
        self.dex = Dex()
        self.bot = MakerBot()
        self.table = Table()
        self.dex.start()

    def start_makerbot(self):
        self.bot.start()

    def update_makerbot(self):
        self.bot.update()

    def reset_makerbot_config(self):
        self.bot.reset_config()

    def stop_makerbot(self):
        self.bot.stop()

    def activate_coins_tui(self):
        while True:
            try:
                coins = color_input("Enter the tickers you want to activate: ").split(
                    " "
                )
                if isinstance(coins, list):
                    dex.activate_coins(coins)
                    break
            except KeyboardInterrupt:
                break

    def task_id_status_tui(self):
        task_ids = list(ACTIVE_TASKS.values())
        if len(task_ids) == 0:
            error_print(f"No active tasks!")
        try:
            task_id = int(color_input(f"Select from active tasks {task_ids}: "))
        except Exception as e:
            error_print(f"task_id must be an integer!")
            return
        if task_id not in task_ids:
            error_print(f"{task_id} not found in active tasks!")
        else:
            dex = Dex()
            for method, task in ACTIVE_TASKS.items():
                if task_id == task:
                    success_print(dex.get_task(method, task_id))

    def view_balances(self):
        self.table.balances(self.dex.enabled_coins_list)

    def view_orders(self):
        self.table.orders(self.dex.api.orders)

    def view_swaps(self):
        self.table.swaps_summary(dex.api.rpc("my_recent_swaps").json())

    def loop_views(self):
        self.table.loop_views()

    def withdraw_funds(self):
        enabled_coins = self.dex.enabled_coins_list
        self.table.balances(enabled_coins)
        if len(enabled_coins) > 0:
            coin = color_input("Enter the ticker of the coin you want to withdraw: ")
            while coin not in enabled_coins:
                error_print(
                    f"{coin} is not enabled. Options are |{'|'.join(enabled_coins)}|, try again."
                )
                coin = color_input(
                    "Enter the ticker of the coin you want to withdraw: "
                )

            amount = color_input(
                f"Enter the amount of {coin} you want to withdraw, or 'MAX' to withdraw full balance: "
            )
            amount = dex.validate_withdraw_amount(amount)
            while not amount:
                error_print(
                    f"{amount} is not 'MAX' or a valid numeric value, try again."
                )
                amount = color_input(
                    f"Enter the amount of {coin} you want to withdraw, or 'MAX' to withdraw full balance: "
                )
                amount = dex.validate_withdraw_amount(amount)

            address = color_input(f"Enter the destination address: ")
            while not dex.is_address_valid(coin, address):
                error_print(f"{address} is not a valid {coin} address, try again.")
                address = color_input(f"Enter the destination address: ")

            resp = dex.withdraw(coin, amount, address)
            if "error" in resp:
                error_print(resp)
            elif "result" in resp:
                if "tx_hex" in resp["result"]:
                    send_resp = dex.send_raw_tx(coin, resp["result"]["tx_hex"])
                    if "tx_hash" in send_resp:
                        success_print(
                            f"{amount} {coin} sent to {address}. TXID: {send_resp['tx_hash']}"
                        )
                    else:
                        error_print(send_resp)
                else:
                    error_print(resp)
            else:
                error_print(resp)

    def exit_tui(self):
        q = color_input("Stop Komodo DeFi Framework on exit? [Y/N]: ")
        while q.lower() not in ["y", "n"]:
            error_print("Invalid option, try again.")
            q = color_input("Stop Komodo DeFi Framework on exit? [Y/N]: ")

        if q.lower() == "y":
            resp = dex.quit()
            if "error" in resp:
                error_print(resp)
            elif "success" in resp:
                status_print("Komodo DeFi Framework has stopped.")
        sys.exit()

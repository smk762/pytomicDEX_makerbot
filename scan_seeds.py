#!/usr/bin/env python3
from lib_atomicdex import *


def update_MM2json(seed_phrase):
    with open("MM2.json", "r") as f:
        mm2_conf = json.load(f)

    mm2_conf.update({"passphrase": seed_phrase})

    with open("MM2.json", "w+") as f:
        json.dump(mm2_conf, f, indent=4)


def scan_electrums_for_balances(seed_phrase, seed_phrases):
    ignore_coins = ["tBLK", "GIN", "LYNX", "PGT", "CIPHS", "VOTE2021", "HUSH3"]
    balance_found = False
    for protocol in ACTIVATE_COMMANDS:
        for coin in ACTIVATE_COMMANDS[protocol]:
            if coin not in ignore_coins:
                try:
                    resp = mm2_proxy(ACTIVATE_COMMANDS[protocol][coin])
                    print(resp)
                    if "balance" in resp:
                        if float(resp["balance"]) > 0:
                            balance_found = True
                            seed_phrases[seed_phrase].update({
                                coin: {
                                    "address":resp["address"],
                                    "balance":resp["balance"],
                                }

                            })
                        else:
                            time.sleep(0.1)
                            print(disable_coin(coin))

                            
                except Exception as e:
                    print("---------------------------")
                    print(f"{coin}: {e}")
                print("---------------------------")
    if balance_found:
        with open('coins', 'w', encoding='utf-8') as f:
            json.dump(coins, f, ensure_ascii=False, indent=4)

 


with open("seed_phrases.json", "r") as f:
    seed_phrases = json.load(f)["seed_phrases"]

seed_phrases_list = list(seed_phrases.keys())
seed_phrases_list.reverse()

for seed_phrase in seed_phrases_list:
    print(f"Scanning Seed: {seed_phrase}")
    update_MM2json(seed_phrase)
    time.sleep(5)
    start_mm2()
    time.sleep(5)

    scan_electrums_for_balances(seed_phrase, seed_phrases)
    stop_mm2()
    time.sleep(5)
#!/usr/bin/env python3

import os
import sys
import time
import json
from const import (
    SCRIPT_PATH,
    TEMP_MM2_JSON_FILE,
    ACTIVATE_COMMANDS,
    SEEDS_FILE,
)
from models import Dex


def update_MM2json(seed_phrase):
    with open(TEMP_MM2_JSON_FILE, "r") as f:
        mm2_conf = json.load(f)
    mm2_conf.update({"passphrase": seed_phrase})
    with open(TEMP_MM2_JSON_FILE, "w+") as f:
        json.dump(mm2_conf, f, indent=4)


def scan_electrums_for_balances(seed_phrase, seed_phrases):
    dex = Dex()
    balance_found = False
    ignore_coins = ["tBLK", "GIN", "LYNX", "PGT", "CIPHS", "VOTE2021", "HUSH3"]
    for protocol in ACTIVATE_COMMANDS:
        for coin in ACTIVATE_COMMANDS[protocol]:
            activation_command = ACTIVATE_COMMANDS[protocol][coin]
            try:
                resp = dex.mm2_proxy(ACTIVATE_COMMANDS[protocol][coin])
                print(resp)
                if "balance" in resp:
                    if float(resp["balance"]) > 0:
                        balance_found = True
                        seed_phrases[seed_phrase].update(
                            {
                                coin: {
                                    "address": resp["address"],
                                    "balance": resp["balance"],
                                }
                            }
                        )
                    else:
                        time.sleep(0.1)
                        dex.disable_coin(coin)

            except Exception as e:
                print("---------------------------")
                print(f"{coin}: {e}")
                print("---------------------------")

    if balance_found:
        with open(SEEDS_FILE, "w", encoding="utf-8") as f:
            json.dump(seed_phrases, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    dex = Dex()
    if os.path.exists(TEMP_MM2_JSON_FILE):
        with open(TEMP_MM2_JSON_FILE, "r") as f:
            MM2_JSON = json.load(f)
            if "passphrase" in MM2_JSON:
                mm2_seed_phrase = MM2_JSON["passphrase"]
    else:
        print(f"{TEMP_MM2_JSON_FILE} found, exiting...")
        sys.exit()

    if not os.path.exists(SEEDS_FILE):
        os.popen(
            f"cp {SCRIPT_PATH}/seed_phrases.example {SEEDS_FILE}"
        )
        time.sleep(1)

    with open(SEEDS_FILE, "r") as f:
        seed_phrases = json.load(f)
        if mm2_seed_phrase not in seed_phrases["seed_phrases"]:
            seed_phrases["seed_phrases"].update({mm2_seed_phrase: {}})
            with open(SEEDS_FILE, "w", encoding="utf-8") as f:
                json.dump(seed_phrases, f, ensure_ascii=False, indent=4)

    seed_phrases_list = list(seed_phrases["seed_phrases"].keys())

    for seed_phrase in seed_phrases_list:
        if seed_phrase != "ENTER_A_SEED_PHRASE_HERE_TO_SCAN_IT":
            print(f"Scanning Seed: {seed_phrase}")
            update_MM2json(seed_phrase)
            time.sleep(5)
            dex.start()
            time.sleep(5)
            scan_electrums_for_balances(seed_phrase, seed_phrases)
            dex.quit()
            time.sleep(5)

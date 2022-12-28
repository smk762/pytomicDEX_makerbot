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
            activation_command = ACTIVATE_COMMANDS[protocol][coin]
            
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
                        disable_coin(coin)

            except Exception as e:
                print("---------------------------")
                print(f"{coin}: {e}")
                print("---------------------------")

    if balance_found:
        with open('seed_phrases.json', 'w', encoding='utf-8') as f:
            json.dump(seed_phrases, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':

    if os.path.exists(f"{SCRIPT_PATH}/MM2.json"):
        with open(f"{SCRIPT_PATH}/MM2.json", "r") as f:
            MM2_JSON = json.load(f)
            if "passphrase" in MM2_JSON:
                mm2_seed_phrase = MM2_JSON["passphrase"]
    else:
        print("No MM2.json found, exiting...")
        sys.exit()

    if not os.path.exists(f"{SCRIPT_PATH}/seed_phrases.json"):
        os.popen(f'cp {SCRIPT_PATH}/seed_phrases.example {SCRIPT_PATH}/seed_phrases.json')
        time.sleep(1)

    with open(f"{SCRIPT_PATH}/seed_phrases.json", "r") as f:
        seed_phrases = json.load(f)
        if mm2_seed_phrase not in seed_phrases["seed_phrases"]:
            seed_phrases["seed_phrases"].update({
                mm2_seed_phrase: {}
            })
            with open(f'{SCRIPT_PATH}/seed_phrases.json', 'w', encoding='utf-8') as f:
                json.dump(seed_phrases, f, ensure_ascii=False, indent=4)


    seed_phrases_list = list(seed_phrases["seed_phrases"].keys())

    for seed_phrase in seed_phrases_list:
        if seed_phrase != "ENTER_A_SEED_PHRASE_HERE_TO_SCAN_IT":
            print(f"Scanning Seed: {seed_phrase}")
            update_MM2json(seed_phrase)
            time.sleep(5)
            start_mm2()
            time.sleep(5)

            scan_electrums_for_balances(seed_phrase, seed_phrases)
            stop_mm2()
            time.sleep(5)
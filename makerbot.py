#!/usr/bin/env python3
import os
import time
from helpers import colorize, color_input, status_print, wait_continue
from models import Tui, Config

tui = Tui()

header = "\
     _  __                     _____       ______ _                                           \n\
    | |/ /                    |  __ \     |  ____(_)                                          \n\
    | ' / ___  _ __ ___   ___ | |  | | ___| |__   _                                           \n\
    |  < / _ \| '_ ` _ \ / _ \| |  | |/ _ \  __| | |                                          \n\
    | . \ (_) | | | | | | (_) | |__| |  __/ |    | |                                          \n\
    |_|\_\___/|_| |_| |_|\___/|_____/ \___|_|    |_|                                          \n\
  __  __           _                    _         \033[94m \033[92m     _                     \n\
 |  \/  |   __ _  | | __   ___   _ __  | |__     \033[94m_|_\033[92m   | |_                   \n\
 | |\/| |  / _` | | |/ /  / _ \ | '__| | '_ \   \033[94m/~ ~\ \033[92m | __|                  \n\
 | |  | | | (_| | |   <  |  __/ | |    | |_) | \033[94m< \033[31m0 0\033[94m >\033[92m | |_   \n\
 |_|  |_|  \__,_| |_|\_\  \___| |_|    |_.__/   \033[94m\_=_/\033[92m   \__|                  \n"

author = "{:^60}".format("Welcome to the Komodo DeFi MakerBot TUI v0.2 by Dragonhound")


def main():
    menu_items = [
        {"Start Makerbot": tui.start_makerbot},
        {"View/Update Makerbot": tui.update_makerbot},
        {"Reset Makerbot Config": tui.reset_makerbot_config},
        {"Stop Makerbot": tui.stop_makerbot},
        {"Activate Coins": tui.activate_coins_tui},
        {"Get Task ID Status": tui.task_id_status_tui},
        {"View Balances": tui.view_balances},
        {"View Orders": tui.view_orders},
        {"View Swaps": tui.view_swaps},
        {"Loop Views": tui.loop_views},
        {"Withdraw Funds": tui.withdraw_funds},
        {"Exit TUI": tui.exit_tui},
    ]
    while True:
        try:
            os.system("clear")
            print(colorize(header, "lightgreen"))
            # print(colorize(author, 'cyan'))
            status_print(tui.dex.status)
            print("")

            try:
                for item in menu_items:
                    print(
                        colorize(" [" + str(menu_items.index(item)) + "] ", "blue")
                        + colorize(list(item.keys())[0], "blue")
                    )
                choice = color_input(" Select menu option: ")
                if int(choice) < 0:
                    raise ValueError
                print("")
                list(menu_items[int(choice)].values())[0]()
                print("")
                wait_continue()
            except (ValueError, IndexError):
                pass
        except KeyboardInterrupt:
            tui.exit_tui()


if __name__ == "__main__":
    while True:
        os.system("clear")
        print("\n")
        with open("logo.txt", "r") as logo:
            for line in logo:
                parts = line.split(" ")
                row = ""
                for part in parts:
                    if part.find("~") == -1:
                        row += colorize(part, "blue")
                    else:
                        row += colorize(part, "black")
                print(row, end="")
                time.sleep(0.04)
            time.sleep(0.4)
        print("\n")
        break
    config = Config()
    config.fix_mm2_json()
    main()

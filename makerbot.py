#!/usr/bin/env python3
import os
import time
from helpers import colorize, color_input, status_print, wait_continue
from models import Tui

tui = Tui()

header = (r"""
     _  __                     _____       ______ _                                           
    | |/ /                    |  __ \     |  ____(_)                                          
    | ' / ___  _ __ ___   ___ | |  | | ___| |__   _                                           
    |  < / _ \| '_ ` _ \ / _ \| |  | |/ _ \  __| | |                                          
    | . \ (_) | | | | | | (_) | |__| |  __/ |    | |                                          
    |_|\_\___/|_| |_| |_|\___/|_____/ \___|_|    |_|                                          
  __  __           _                    _         {ESC}[94m {ESC}[92m     _                     
 |  \/  |   __ _  | | __   ___   _ __  | |__     {ESC}[94m_|_{ESC}[92m   | |_                   
 | |\/| |  / _` | | |/ /  / _ \ | '__| | '_ \   {ESC}[94m/~ ~\ {ESC}[92m | __|                  
 | |  | | | (_| | |   <  |  __/ | |    | |_) | {ESC}[94m< {ESC}[31m0 0{ESC}[94m >{ESC}[92m | |_   
 |_|  |_|  \__,_| |_|\_\  \___| |_|    |_.__/   {ESC}[94m\_=_/{ESC}[92m   \__|                  
""").format(ESC="\033")

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
        {"View Docs": tui.view_docs},
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

    main()

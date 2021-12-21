#!/usr/bin/env python3
from lib_atomicdex import *
import lib_tui


header = "\
            _                  _      _____  ________   __  \n\
       /\  | |                (_)    |  __ \|  ____\ \ / /  \n\
      /  \ | |_ ___  _ __ ___  _  ___| |  | | |__   \ V /   \n\
     / /\ \| __/ _ \| '_ ` _ \| |/ __| |  | |  __|   > <    \n\
    / ____ \ || (_) | | | | | | | (__| |__| | |____ / . \   \n\
   /_/    \_\__\___/|_| |_| |_|_|\___|_____/|______/_/ \_\  \n\
  __  __           _                    _         .     _   \n\
 |  \/  |   __ _  | | __   ___   _ __  | |__     _*_   | |_ \n\
 | |\/| |  / _` | | |/ /  / _ \ | '__| | '_ \   /   \  | __|\n\
 | |  | | | (_| | |   <  |  __/ | |    | |_) | | 0 0 | | |_ \n\
 |_|  |_|  \__,_| |_|\_\  \___| |_|    |_.__/   \_^_/   \__|\n"

author = '{:^60}'.format('Welcome to the AtomicDEX MakerBot TUI v0.1 by Thorn Mennet')

def main():
    menu_items = [
        {"Start Makerbot": lib_tui.start_makerbot},
        {"Update Makerbot": lib_tui.update_makerbot},
        {"Stop Makerbot": lib_tui.stop_makerbot},
        {"Activate Coins": lib_tui.activate_coins_tui},
        {"View Balances": lib_tui.view_balances},
        {"View Orders": lib_tui.view_orders},
        {"View Swaps": lib_tui.view_swaps},
        {"Exit TUI": lib_tui.exit_tui}
    ]
    while True:
        os.system('clear')
        print(colorize(header, 'lightgreen'))
        print(colorize(author, 'cyan'))
        # Add status: order count, swaps in progress, delta
        try:
            for item in menu_items:
                print(colorize(" [" + str(menu_items.index(item)) + "] ", 'blue') + colorize(list(item.keys())[0],'blue'))
            choice = color_input(" Select menu option: ")
            if int(choice) < 0:
                raise ValueError
            print("")
            list(menu_items[int(choice)].values())[0]()
            print("")
            wait_continue()
        except (ValueError, IndexError):
            pass



if __name__ == "__main__":
    while True:
        os.system('clear')
        print("\n")
        with (open("logo.txt", "r")) as logo:
            for line in logo:
                parts = line.split(' ')
                row = ''
                for part in parts:
                    if part.find('.') == -1:
                        row += colorize(part, 'blue')
                    else:
                        row += colorize(part, 'black')
                print(row, end='')
                #print(line, end='')
                time.sleep(0.04)
            time.sleep(0.4)
        print("\n")
        break
    main()
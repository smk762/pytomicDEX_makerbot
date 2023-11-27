#!/usr/bin/env python3
from models import MakerBot, Table

bot = MakerBot()
table = Table()
bot.activate_bot_coins()
table.loop_views()

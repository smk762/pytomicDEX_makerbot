# PytomicDEX Makerbot

A Terminal User Interface (TUI) for automated trading with [Komodo Platform's](https://komodoplatform.com/) [Komodo DeFi Framework](https://github.com/KomodoPlatform/komodo-defi-framework)


![PytomicDEX-makerbot](https://user-images.githubusercontent.com/35845239/147382522-b35fa70d-60ad-41c5-a091-d864a6750cfb.png)


# Install

```bash
sudo apt install wget curl jq git python3-pip
git clone https://github.com/smk762/pytomicDEX_makerbot/
cd pytomicDEX_makerbot
pip3 install -r requirements.txt
./makerbot.py
```

# Recommended

- [Terminator](https://www.linuxshelltips.com/terminator-terminal-emulator/)
- [Komodo Platform](https://komodoplatform.com/)
- [AtomicDEX GUI (Desktop and mobile)](https://www.atomicdex.io/)
- [AtomicDEX API Repository](https://github.com/KomodoPlatform/komodo-defi-framework/)
- [Komodo DeFi Framework Developer Docs](https://developers.komodoplatform.com/basic-docs/atomicdex/introduction-to-atomicdex.html)


# Walkthrough

[![Watch the video](https://user-images.githubusercontent.com/35845239/147961225-ec910ec2-7c73-47d1-afc0-3033958e50cc.png)](https://odysee.com/@Dragonhound:7/pytomicDEX-makerbot:8)


# Configuration
- Initial config is done through the TUI on first launch, and stored in the `config` folder.
- You can modify the config in the TUI with `View/Update Makerbot`
- You can customise pair configs in `makerbot_command_params.json` for min/max trade and spread.
- You can edit `bot_settings.json` manually to add coins or change defaults, which will be applied to `makerbot_command_params.json` next time you launch the TUI.
- Existing customised pair configs in `makerbot_command_params.json` will be retained if the base/quote coins are still in `bot_settings.json`.
- To completely reset your config, select `Reset Makerbot Config` in the TUI.


# Warning

Use this with small amounts you are comfortable with and be conscious of your risk tolerance. Always make a secure offline backup of your seed phrase. 

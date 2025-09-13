#!/bin/bash
wget https://raw.githubusercontent.com/KomodoPlatform/coins/master/coins -O coins
mkdir -p ../config
wget https://raw.githubusercontent.com/KomodoPlatform/coins/master/utils/coins_config.json -O ../config/coins_config.json
wget https://raw.githubusercontent.com/KomodoPlatform/coins/master/seed-nodes.json -O ../config/seed-nodes.json

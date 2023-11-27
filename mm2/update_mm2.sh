#!/bin/bash

rm mm2

# For release binaries
# wget $(curl -vvv https://api.github.com/repos/KomodoPlatform/komodo-defi-framework/releases | jq -r '.[0].assets | map(select(.name | contains("Linux-Release."))) | .[0].browser_download_url') -O mm2.zip
# unzip mm2.zip
# rm mm2.zip

# For dev binaries
wget https://sdk.devbuilds.komodo.earth/dev/mm2_0221505-linux-x86-64.zip
unzip mm2_0221505-linux-x86-64.zip
rm mm2_0221505-linux-x86-64.zip

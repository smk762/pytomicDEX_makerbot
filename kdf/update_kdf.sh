#!/bin/bash

rm mm2 || true
rm kdf || true

# For release binaries
wget $(curl -vvv https://api.github.com/repos/KomodoPlatform/komodo-defi-framework/releases | jq -r '.[0].assets | map(select(.name | contains("Linux-Release."))) | .[0].browser_download_url') -O kdf.zip
unzip kdf.zip
rm kdf.zip


#!/bin/zsh
cd -- "$(dirname -- "$0")"
echo "HandPilot Car: http://localhost:4173"
echo "Durdurmak için Control + C tuşlarına basın."
python3 -m http.server 4173

#!/bin/zsh
set -euo pipefail

cd /Users/mengleang/Desktop/ktx_portal
set -a
source ./.env
set +a

exec /Users/mengleang/Desktop/ktx_portal/.venv/bin/python run.py

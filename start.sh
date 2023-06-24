#!/usr/bin/env bash
set -o errexit -o nounset -o pipefail
pip install -r requirements.txt
python3 main.py

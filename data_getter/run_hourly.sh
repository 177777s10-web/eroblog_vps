#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
# ここでは venv を使わず、必要なら上で source を足す運用に合わせる
API_ID="${API_ID:-nAguP939XQHSFhANAPC9}" \
AFFILIATE_ID="${AFFILIATE_ID:-shinya39-995}" \
python eroblog/run.py --auto

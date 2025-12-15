#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${API_ID:?API_ID is required}"
: "${AFFILIATE_ID:?AFFILIATE_ID is required}"
exec .venv/bin/python blog_videoc_today.py

#!/usr/bin/env bash
set -u

OUT="/root/eroblog/data_getter/out/videoc_latest_enriched.jsonl"
BK="${OUT}.bak"

echo "[env] API_ID=${API_ID:+SET} AFFILIATE_ID=${AFFILIATE_ID:+SET}"

# 直前のjsonlを退避（無ければ無視）
cp -a "$OUT" "$BK" 2>/dev/null || true

echo "[1/2] getter: data_getter venv (cwd=/root/eroblog/data_getter)"
cd /root/eroblog/data_getter

set +e
/root/eroblog/data_getter/.venv/bin/python blog_videoc_today.py
RC=$?
set -e

if [ "$RC" -ne 0 ]; then
  echo "[ERR] getter failed rc=$RC"
  if [ -s "$BK" ]; then
    cp -a "$BK" "$OUT"
    echo "[RECOVER] restored jsonl from backup"
  fi
  exit "$RC"
fi

if [ ! -s "$OUT" ]; then
  echo "[ERR] jsonl is empty after getter"
  if [ -s "$BK" ]; then
    cp -a "$BK" "$OUT"
    echo "[RECOVER] restored jsonl from backup"
  fi
  exit 2
fi

echo "[2/2] publish: blog_builder venv"
cd /root/eroblog/blog_builder
/root/eroblog/blog_builder/.venv/bin/python manage.py auto_hourly_publish

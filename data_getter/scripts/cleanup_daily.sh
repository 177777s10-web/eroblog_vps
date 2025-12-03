#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
find out/items -type f -name '*_probe_pw.json' -mtime +30 -delete || true
find out/items -type f -name '*_samples.json'   -mtime +30 -delete || true
find logs -type f -mtime +30 -delete || true
mkdir -p out/archive
for f in out/videoc_latest_enriched.jsonl out/videoc_latest.csv; do
  [ -s "$f" ] && cp -p "$f" "out/archive/$(basename "$f").$(date +%Y%m)"
done
prev=$(date -d 'last month' +%Y%m)
ls out/archive/*.$prev 1>/dev/null 2>&1 && gzip -f out/archive/*.$prev || true

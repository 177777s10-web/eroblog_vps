#!/usr/bin/env bash
set -euo pipefail
N="${1:-30}"                              # 取得本数（既定30）
BASE="$HOME/eroblog/data_getter"
OUT="$HOME/eroblog/content/exports/batch_$(date +%Y%m%d-%H%M%S)"
JSONL="$OUT/batch.jsonl"
CSV="$OUT/batch.csv"
LOG="$OUT/batch.log"

mkdir -p "$OUT"

echo "[INFO] start batch N=$N -> $OUT" | tee -a "$LOG"

have_header=0
for i in $(seq 1 "$N"); do
  echo "[RUN] $i/$N" | tee -a "$LOG"

  # 未処理の最新を1本取得（既存履歴で重複回避）
  python "$BASE/blog_videoc_today.py" --auto 2>&1 | tee -a "$LOG"

  # 取得結果（最新1行）を集約ファイルに追記
  head -n1 "$BASE/out/videoc_latest_enriched.jsonl" >> "$JSONL"

  if [ $have_header -eq 0 ]; then
    # CSVは最初にヘッダ行を作る
    head -n1 "$BASE/out/videoc_latest.csv" > "$CSV"
    have_header=1
  fi
  # CSVのデータ行を追記
  tail -n1 "$BASE/out/videoc_latest.csv" >> "$CSV"

  # 連続アクセス緩和
  sleep 5
done

# サマリ表示
echo "[DONE] JSONL lines: $(wc -l < "$JSONL"), CSV rows: $(($(wc -l < "$CSV")-1))" | tee -a "$LOG"

#!/usr/bin/env bash
set -euo pipefail

# 既存crontab取得（無ければ空）
TMP=$(mktemp)
crontab -l 2>/dev/null > "$TMP" || true

# data_getter 以外の cleanup_daily.sh を除去
grep -v -E 'cleanup_daily\.sh"$' "$TMP" \
| grep -v -E 'cd ~/eroblog_project_GPT && ./scripts/cleanup_daily\.sh' \
| grep -v -E 'cd ~/eroblog && ./scripts/cleanup_daily\.sh' \
> "${TMP}.filtered" || true

# 期待する1行（重複防止のため一意化）
WANTED='10 0 * * * bash -lc "cd ~/eroblog/data_getter && ./scripts/cleanup_daily.sh"'
{ echo "$WANTED"; cat "${TMP}.filtered"; } \
| awk '!seen[$0]++' \
> "${TMP}.new"

# 反映
crontab "${TMP}.new"
rm -f "$TMP" "${TMP}.filtered" "${TMP}.new"

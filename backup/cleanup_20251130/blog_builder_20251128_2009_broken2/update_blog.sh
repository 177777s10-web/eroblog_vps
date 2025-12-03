#!/usr/bin/env bash
set -e

# このスクリプト自身の場所（blog_builder）へ移動
cd "$(dirname "$0")"

# 仮想環境を有効化
source .venv/bin/activate

# 1) 記事インポート
#   scripts/配下から posts を見つけられるように PYTHONPATH を blog_builder に通す
PYTHONPATH="$(pwd)" python scripts/import_posts.py

# 2) sizes を history.jsonl から同期（空のものだけ埋める）
python manage.py sync_sizes_from_history

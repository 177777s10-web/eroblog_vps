#!/usr/bin/env bash
set -eu

set -a
. /etc/eroblog.env
set +a

GETTER_PY="/root/eroblog/data_getter/.venv/bin/python"
BLOG_PY="/root/eroblog/blog_builder/.venv/bin/python"
JSONL="/root/eroblog/data_getter/out/videoc_latest_enriched.jsonl"

cd /root/eroblog/data_getter
$GETTER_PY blog_videoc_today.py

cd /root/eroblog/blog_builder
$BLOG_PY manage.py auto_populate_content --jsonl "$JSONL"

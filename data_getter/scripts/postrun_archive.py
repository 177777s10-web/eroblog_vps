# -*- coding: utf-8 -*-
import json, os
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parents[1]   # eroblog/data_getter
EROBLOG = BASE.parent
LATEST = BASE / "out" / "videoc_latest_enriched.jsonl"
HIST   = BASE / "out" / "history.jsonl"
DAILY_DIR = BASE / "out" / "daily"
EXPORT = EROBLOG / "content" / "exports" / "latest.jsonl"

DAILY_DIR.mkdir(parents=True, exist_ok=True)

def read_last_nonempty(path: Path):
    if not path.exists(): return None
    last = None
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last = json.loads(line)
    return last

def already_in_daily(day_path: Path, cid: str) -> bool:
    if not day_path.exists(): return False
    with day_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("cid") == cid:
                return True
    return False

def main():
    if not LATEST.exists():
        print("[INFO] latest jsonl not found"); return
    with LATEST.open(encoding="utf-8") as f:
        rec = None
        for ln in f:
            if ln.strip():
                rec = json.loads(ln)
    if not rec:
        print("[INFO] latest jsonl empty"); return

    # 付加情報
    rec.setdefault("_ts", (__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()))
    day = (rec.get("date") or datetime.now().strftime("%Y-%m-%d")).split(" ")[0].replace("-","")
    day_path = DAILY_DIR / f"{day}.jsonl"

    # exports/latest.jsonl に同期（上書き）
    EXPORT.parent.mkdir(parents=True, exist_ok=True)
    EXPORT.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")

    # history.jsonl（末尾とCIDが同じならスキップ）
    prev = read_last_nonempty(HIST)
    if not prev or prev.get("cid") != rec.get("cid"):
        with HIST.open("a", encoding="utf-8") as w:
            w.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("[OK] history appended:", rec.get("cid"))
    else:
        print("[SKIP] history same cid:", rec.get("cid"))

    # daily/YYYYMMDD.jsonl（同一日内で同一CIDは重複登録しない）
    if already_in_daily(day_path, rec.get("cid")):
        print("[SKIP] daily already has:", rec.get("cid"))
    else:
        with day_path.open("a", encoding="utf-8") as w:
            w.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("[OK] daily appended:", day_path.name, rec.get("cid"))

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
from datetime import datetime
from generate_draft import EROBLOG, DRAFTS_DIR, QUEUE_DIR, slug, build_markdown

BASE   = Path(EROBLOG, "data_getter")
DAILY  = BASE / "out" / "daily"

def iter_daily(date_str: str):
    fp = DAILY / f"{date_str}.jsonl"
    if not fp.exists():
        print(f"[FAIL] daily not found: {fp}")
        return
    with fp.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue

def write_md_and_queue(d: dict):
    cid = d.get("cid") or ""
    title = d.get("title") or ""
    safe = slug(title) or "untitled"
    date_for_name = (d.get("date") or datetime.now().strftime("%Y-%m-%d")).split(" ")[0].replace("-","")
    md_name = f"{date_for_name}_{cid}_{safe}.md"
    md_path = DRAFTS_DIR / md_name
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    md = build_markdown(d)
    md_path.write_text(md, encoding="utf-8")

    q = {"cid": cid, "draft_path": str(md_path.relative_to(EROBLOG)),
         "ready": True, "title": title, "date": d.get("date")}
    (QUEUE_DIR / f"{cid}.json").write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path

def main():
    date_str = sys.argv[1] if len(sys.argv) >= 2 else datetime.now().strftime("%Y%m%d")
    count = 0
    for rec in iter_daily(date_str):
        md = write_md_and_queue(rec)
        count += 1
        print(f"[OK] draft+queue: {md.name}")
    print(f"[DONE] {count} items from daily {date_str}")

if __name__ == "__main__":
    main()

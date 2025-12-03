# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
from datetime import datetime

# 既存の generate_draft を利用
from generate_draft import EROBLOG, DRAFTS_DIR, QUEUE_DIR, slug, build_markdown

BASE  = Path(EROBLOG, "data_getter")
JSONL = BASE / "out" / "videoc_latest_enriched.jsonl"
ITEMS = BASE / "out" / "items"

def load_from_jsonl(cid: str):
    if not JSONL.exists():
        return None
    hit = None
    with JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("cid") == cid:
                hit = d
    return hit

def merge_api_probe(cid: str):
    api_path   = ITEMS / f"{cid}_api.json"
    probe_path = ITEMS / f"{cid}_probe_pw.json"
    if not api_path.exists() and not probe_path.exists():
        return None

    api, probe = {}, {}
    try:
        if api_path.exists():
            api = json.loads(api_path.read_text(encoding="utf-8"))
    except Exception:
        api = {}
    try:
        if probe_path.exists():
            probe = json.loads(probe_path.read_text(encoding="utf-8"))
    except Exception:
        probe = {}

    out = dict(api)
    for k in ("review_html","review","review_body","description","sizes","sizes_text","name","label","sample_images"):
        v = probe.get(k)
        if v and not out.get(k):
            out[k] = v
    for k in ("genres","maker","series","performers"):
        if k in api:
            out[k] = api[k]
        elif k in probe and k not in out:
            out[k] = probe[k]

    out["cid"] = cid
    return out

def write_md_and_queue(data: dict):
    cid   = data.get("cid")
    title = data.get("title","")
    date_for_name = (data.get("date") or datetime.now().strftime("%Y-%m-%d")).split(" ")[0].replace("-", "")
    md_name = f"{date_for_name}_{cid}_{slug(title)}.md"
    md_path = DRAFTS_DIR / md_name
    md_path.parent.mkdir(parents=True, exist_ok=True)

    md = build_markdown(data)
    md_path.write_text(md, encoding="utf-8")

    q = {
        "cid": cid,
        "draft_path": str(md_path.relative_to(EROBLOG)),
        "ready": True,
        "title": data.get("title"),
        "date": data.get("date"),
    }
    (QUEUE_DIR / f"{cid}.json").write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path

def main():
    if len(sys.argv) < 2:
        print("Usage: python regen_draft_by_cid.py <cid>")
        return
    cid = sys.argv[1].strip()

    data = load_from_jsonl(cid)
    if not data:
        data = merge_api_probe(cid)
    if not data:
        print(f"[FAIL] JSONLにもitemsにも {cid} のデータが見つかりません。")
        return

    md_path = write_md_and_queue(data)
    print(f"[OK] 再生成: {md_path}")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
import json, re
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parents[1]          # eroblog/data_getter
EROBLOG = BASE.parent                                # eroblog/
JSONL_PATH = BASE / "out" / "videoc_latest_enriched.jsonl"
DRAFTS_DIR = EROBLOG / "content" / "drafts"
QUEUE_DIR = EROBLOG / "publish_queue"

DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

def slug(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[ \t]+", "_", s)
    s = re.sub(r"[^\w\-_.ぁ-んァ-ン一-龯]", "", s)
    return s[:80] or "untitled"

def read_last_json(path: Path):
    if not path.exists():
        return None
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        buf = b""
        step = 4096
        pos = size
        while pos > 0:
            n = min(step, pos)
            pos -= n
            f.seek(pos)
            buf = f.read(n) + buf
            if b"\n" in buf:
                break
        for line in reversed(buf.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line.decode("utf-8"))
            except Exception:
                return None
    return None

def pick_review(d: dict) -> str:
    for k in ("review_html", "review", "review_body", "description"):
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "（レビュー本文がありません。）"

def build_markdown(d: dict) -> str:
    cid = d.get("cid", "")
    title = d.get("title", "タイトル不明")
    name = d.get("name") or d.get("performers") or "-"
    maker = d.get("maker") or "-"
    label = d.get("label") or "-"
    sizes = d.get("sizes") or d.get("sizes_text") or "B-- W-- H--"
    genres = d.get("genres") or []
    review = pick_review(d)
    date_raw = (d.get("date") or "").split(" ")[0]
    try:
        dt = datetime.strptime(date_raw, "%Y-%m-%d")
    except Exception:
        dt = datetime.now()
    date_str = dt.strftime("%Y-%m-%d")

    # タグは上限なし（重複除去・順序維持）
    tags = [t for t in (genres or []) if t]
    seen=set()
    tags = [x for x in tags if not (x in seen or seen.add(x))]

    front = [
        "---",
        f'cid: "{cid}"',
        f'title: "{title}"',
        f'date: "{date_str}"',
        f'poster_image: "../assets/{cid}_poster.jpg"',
        "tags:",
    ]
    for t in tags:
        front.append(f'  - "{t}"')
    front.append("---\n")

    body = []
    body.append(f"# {title}\n")
    body.append("## 基本情報\n")
    body.append(f"* 出演者: {name}")
    body.append(f"* メーカー: {maker}")
    body.append(f"* レーベル: {label}")
    body.append(f"* サイズ: {sizes}")
    body.append(f"* アフィリエイトURL: {d.get('affiliate_url') or '-'}")
    body.append(f"* サンプル動画: {d.get('sample_movie_url') or '-'}\n")
    body.append("## レビュー\n")
    body.append(review + "\n")
    body.append("## サンプル画像（ある場合）\n")
    for i in range(1, 6):
        body.append(f"![sample {i}](../assets/{cid}_{i:02d}.jpg)")
    body.append("")
    return "\n".join(front + body)

def main():
    data = read_last_json(JSONL_PATH)
    if not data:
        print("[FAIL] JSONLの末尾から有効なデータを取得できませんでした。")
        return

    cid = data.get("cid")
    if not cid:
        print("[FAIL] cid が見つかりません。")
        return

    safe_title = slug(data.get("title", ""))
    date_for_name = (data.get("date") or datetime.now().strftime("%Y-%m-%d")).split(" ")[0].replace("-", "")
    md_name = f"{date_for_name}_{cid}_{safe_title}.md"
    draft_path = DRAFTS_DIR / md_name

    if not draft_path.exists():
        md = build_markdown(data)
        draft_path.write_text(md, encoding="utf-8")
        print(f"[OK] 原稿生成: {draft_path.name}")
    else:
        print(f"[SKIP] 既存原稿: {draft_path.name}")

    queue = {
        "cid": cid,
        "draft_path": str(draft_path.relative_to(EROBLOG)),
        "ready": True,
        "title": data.get("title"),
        "date": data.get("date"),
    }
    (QUEUE_DIR / f"{cid}.json").write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 公開キュー: {cid}.json")

if __name__ == "__main__":
    main()

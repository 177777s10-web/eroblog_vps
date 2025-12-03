# -*- coding: utf-8 -*-
import json, subprocess, sys, html, datetime
from pathlib import Path

BASE   = Path(__file__).resolve().parents[1]
OUTDIR = BASE / "out"
JSONL  = OUTDIR / "videoc_latest_enriched.jsonl"
ITEMS  = OUTDIR / "items"

def sh(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(p.stderr.strip())
    return p.stdout

def load_enriched():
    if not JSONL.exists():
        raise SystemExit("out/videoc_latest_enriched.jsonl がありません")
    line = [l for l in JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not line:
        raise SystemExit("enriched.jsonl が空です")
    return json.loads(line[0])

def ensure_api_json(cid):
    api_path = ITEMS / f"{cid}_api.json"
    if api_path.exists():
        return json.loads(api_path.read_text(encoding="utf-8"))
    # 取得（既存の api_fetch_by_cid.py を利用）
    js = sh(f'{sys.executable} fanza/api_fetch_by_cid.py --cid "{cid}"')
    data = json.loads(js)
    api_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data

def load_probe_json(cid):
    # 既存の probe 出力（videoc_probe.py が吐いたもの）
    probe_path = ITEMS / f"{cid}_probe_pw.json"
    if not probe_path.exists():
        # なければ直取得（副作用：ファイル生成）
        url = f"https://video.dmm.co.jp/amateur/content/?id={cid}"
        js = sh(f'{sys.executable} fanza/videoc_probe.py "{url}"')
        data = json.loads(js)
        probe_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data
    return json.loads(probe_path.read_text(encoding="utf-8"))

def val(d, *keys, default=""):
    for k in keys:
        if k in d and d[k]:
            return d[k]
    return default

def main():
    enr = load_enriched()
    cid = enr.get("cid")
    if not cid:
        raise SystemExit("enriched に cid がありません")
    api   = ensure_api_json(cid)
    probe = load_probe_json(cid)

    # 表示項目の定義
    rows = []
    def add(label, k_api, k_probe, k_enr, transform=lambda x:x):
        a = transform(val(api, k_api, default=""))
        p = transform(val(probe, k_probe, default=""))
        e = transform(val(enr, k_enr, default=""))
        rows.append((label, a, p, e))

    add("CID",                "cid",           "cid",           "cid")
    add("タイトル",           "title",         "title",         "title")
    add("名前",               "name",          "name",          "name")
    add("レーベル/シリーズ",   "label",         "label",         "label")
    add("BWH(テキスト)",      "sizes_text",    "sizes",         "sizes")
    add("ポスターURL",        "poster_url",    "poster_url",    "poster_url")
    add("サンプル動画URL",     "sample_movie",  "sample_movie_url","sample_movie_url")
    add("アフィURL",          "affiliate",     "affiliate_url", "affiliate_url")
    add("レビュー文字数",     "review",        "review_body",   "review",
        transform=lambda s: str(len(s or "")))
    add("画像枚数",           "sample_images", "sample_images", "sample_images",
        transform=lambda arr: str(len(arr) if isinstance(arr, list) else 0))

    # CSV出力
    csv_path = OUTDIR / "report_latest.csv"
    import csv
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Field","API","Scrape","Chosen(enriched)"])
        for r in rows:
            w.writerow(r)

    # HTML出力（横並び）
    html_path = OUTDIR / "report_latest.html"
    def esc(x): 
        if isinstance(x, list): 
            return html.escape(", ".join(map(str,x)))
        return html.escape(str(x))
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    with html_path.open("w", encoding="utf-8") as w:
        w.write("<meta charset='utf-8'>")
        w.write(f"<h2>最新1件レポート（{esc(cid)}）</h2>")
        w.write(f"<div>generated at {now}</div>")
        w.write("<style>table{border-collapse:collapse;font-family:sans-serif;} td,th{border:1px solid #ccc;padding:6px 8px;} th{background:#f7f7f7;} .mono{font-family:monospace;}</style>")
        w.write("<table>")
        w.write("<tr><th>Field</th><th>API</th><th>Scrape</th><th>Chosen(enriched)</th></tr>")
        for fld,a,p,e in rows:
            w.write("<tr>")
            w.write(f"<td>{esc(fld)}</td>")
            w.write(f"<td class='mono'>{esc(a)}</td>")
            w.write(f"<td class='mono'>{esc(p)}</td>")
            w.write(f"<td class='mono'>{esc(e)}</td>")
            w.write("</tr>")
        w.write("</table>")

        # 画像プレビュー
        sims = enr.get("sample_images") or []
        if sims:
            w.write("<h3>画像プレビュー</h3><div>")
            for u in sims[:20]:
                w.write(f"<div style='display:inline-block;margin:4px'><img src='{esc(u)}' style='height:120px'></div>")
            w.write("</div>")

        # レビュー本文
        rev = val(enr, "review_body","review","description", default="")
        if rev:
            w.write("<h3>レビュー（enriched）</h3>")
            w.write(f"<div style='white-space:pre-wrap;border:1px solid #ccc;padding:8px'>{esc(rev)}</div>")

    print("CSV:", csv_path)
    print("HTML:", html_path)

if __name__ == "__main__":
    main()

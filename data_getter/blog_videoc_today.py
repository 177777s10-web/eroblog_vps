# -*- coding: utf-8 -*-
import os, sys, json, re, subprocess, csv, datetime, urllib.request, urllib.parse as up

# ---- FANZA API env bootstrap (auto-added) ----
def _ensure_fanza_env():
    import os, sys
    if os.environ.get("API_ID") and os.environ.get("AFFILIATE_ID"):
        return
    try:
        from pathlib import Path as _P
        root = _P(__file__).resolve().parents[1]  # eroblog/
        sys.path.append(str(root / "blog_builder"))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog_builder.settings")
        import django
        django.setup()
        try:
            from posts.models import SiteSettings
        except Exception:
            SiteSettings = None
        api_id = aff_id = None
        if SiteSettings:
            st = SiteSettings.objects.first()
            if st:
                api_id = getattr(st, "api_id", None)
                aff_id = getattr(st, "affiliate_id", None)
        if api_id and aff_id:
            os.environ.setdefault("API_ID", api_id)
            os.environ.setdefault("AFFILIATE_ID", aff_id)
        else:
            print("[WARN] SiteSettings から API_ID/AFFILIATE_ID を取得できませんでした")
    except Exception as e:
        print("[WARN] _ensure_fanza_env で例外:", e)
# ----------------------------------------------
from pathlib import Path

BASE  = Path(__file__).resolve().parent
OUT   = BASE / "out" / "items"
JSONL = BASE / "out" / "videoc_latest_enriched.jsonl"
CSV   = BASE / "out" / "videoc_latest.csv"
HIST  = BASE / "out" / "processed_cids.txt"
# 🔽 --- GEMINI 追記 --- 🔽
# content/assets/ へのパス
ASSETS = BASE.parent / "content" / "assets"
# 偽装ヘッダー
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'Referer': 'https://www.dmm.co.jp/'
}
# 🔼 --- GEMINI 追記 --- 🔼

API_HOST = "https://api.dmm.com/affiliate/v3/ItemList"
ALLOW_HOSTS = ("pics.dmm.co.jp","awsimgsrc.dmm.co.jp")
EXTS = (".jpg",".jpeg",".webp",".png")

def run(cmd: str) -> str:
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed: {cmd}\n{p.stderr}")
    return p.stdout

def api_one(cid: str) -> dict:
    js  = run(f'{sys.executable} fanza/api_fetch_by_cid.py --cid "{cid}"')
    return json.loads(js)

def probe_one(cid: str) -> dict:
    url = f"https://video.dmm.co.jp/amateur/content/?id={cid}"
    js  = run(f'{sys.executable} fanza/videoc_probe.py "{url}"')
    d   = json.loads(js)
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{cid}_probe_pw.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return d

def samples_one(cid):
    import json, subprocess, sys
    from pathlib import Path
    outp = Path(f"out/items/{cid}_samples.json")

    # 無ければ生成
    if not outp.exists():
        cmd = f'{sys.executable} scripts/fetch_exact_samples.py --cid "{cid}" --out "{outp}" --headless true --timeout 120000'
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"fetch_exact_samples failed: {p.stderr}")

    # 大サイズへの昇格（あれば）
    upgr = Path("scripts/upgrade_samples_to_large.py")
    if upgr.exists():
        cmd = f'{sys.executable} "{upgr}" "{outp}"'
        subprocess.run(cmd, shell=True, capture_output=True, text=True)

    try:
        d = json.loads(outp.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    imgs = d.get("sample_images") or []
    # 念のため、現在CID以外・拡張子不正を除外
    import re as _re
    keep = []
    pat = _re.compile(rf"/digital/amateur/{cid}/.*{cid}jp-[0-9]+\.(jpg|jpeg|webp|png)$", _re.I)
    for u in imgs:
        if not u: 
            continue
        base = u.split("?",1)[0].split("#",1)[0]
        if pat.search(base):
            keep.append(base)
    return keep or imgs


def merge_and_append(enriched):
    JSONL.parent.mkdir(parents=True, exist_ok=True)
    with JSONL.open("a", encoding="utf-8") as w:
        w.write(json.dumps(enriched, ensure_ascii=False) + "\n")

def write_csv_row(d):
    CSV.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "cid","title","genres","maker","series","performers_count",
        "name","label","sizes","poster_url","sample_movie_url","affiliate_url",
        "review_len","images_count","ts_iso"
    ]
    exists = CSV.exists()
    with CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        if not exists: w.writeheader()
        w.writerow({
            "cid": d.get("cid"),
            "title": d.get("title"),
            "genres": " / ".join(d.get("genres") or []),
            "maker": d.get("maker"),
            "series": d.get("series"),
            "performers_count": len(d.get("performers") or []),
            "name": d.get("name"),
            "label": d.get("label"),
            "sizes": d.get("sizes") or d.get("sizes_text"),
            "poster_url": d.get("poster_url"),
            "sample_movie_url": d.get("sample_movie_url"),
            "affiliate_url": d.get("affiliate_url"),
            "review_len": len((d.get("review_body") or d.get("review") or d.get("description") or "")),
            "images_count": len(d.get("sample_images") or []),
            "ts_iso": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        })

# 🔽 --- GEMINI 追記 --- 🔽
def download_file(url: str, dest_path: Path) -> bool:
    """ 偽装ヘッダー付きでファイルをダウンロードする """
    try:
        print(f"  Downloading: {url}")
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as response:
            with open(dest_path, 'wb') as out_file:
                out_file.write(response.read())
        return True
    except Exception as e:
        print(f"  └ Failed: {e}")
        return False

def download_assets_for_post(enriched: dict):
    """
    content/assets/ にポスターとサンプル画像を自動ダウンロードする
    """
    cid = enriched.get("cid")
    if not cid:
        print("[WARN] download_assets: CID not found in enriched data.")
        return

    ASSETS.mkdir(parents=True, exist_ok=True)
    print(f"[DOWNLOAD] Checking assets for {cid}...")

    # 1. poster_url (APIがくれた jm.jpg を尊重)
    poster_url = enriched.get("poster_url")
    if poster_url:
        poster_ext = (os.path.splitext(poster_url)[1] or ".jpg").split('?')[0]
        poster_dest = ASSETS / f"{cid}_poster{poster_ext}"
        
        if not poster_dest.exists():
            if download_file(poster_url, poster_dest):
                print(f"  Saved poster: {poster_dest.name}")
            else:
                print(f"  Skip poster: {poster_url}")
        else:
            print(f"  Exists poster: {poster_dest.name}")

    # 2. sample_images
    sample_images = enriched.get("sample_images") or []
    for j, u in enumerate(sample_images):
        ext = (os.path.splitext(u)[1] or ".jpg").split('?')[0]
        dest = ASSETS / f"{cid}_{j+1:02d}{ext}"
        
        if not dest.exists():
            if download_file(u, dest):
                print(f"  Saved sample: {dest.name}")
        else:
            print(f"  Exists sample: {dest.name}")
    
    print(f"[DOWNLOAD] Asset check for {cid} complete.")
# 🔼 --- GEMINI 追記 --- 🔼


def get_api_keys():
    aid = os.environ.get("API_ID") or os.environ.get("DMM_API_ID") or "nAguP939XQHSFhANAPC9"
    aff = os.environ.get("AFFILIATE_ID") or os.environ.get("DMM_AFFILIATE_ID") or "shinya39-995"
    if not aid or not aff: raise RuntimeError("APIキー未設定(API_ID/AFFILIATE_ID)")
    return aid, aff

def call_itemlist_variant(aid, aff, site, service, floor, offset=1, hits=50):
    params = {"api_id":aid,"affiliate_id":aff,"output":"json","sort":"date","hits":hits,"offset":offset}
    if site:    params["site"]=site
    if service: params["service"]=service
    if floor:   params["floor"]=floor
    url = API_HOST + "?" + up.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as resp:
        body = resp.read().decode("utf-8","replace")
    return json.loads(body)

def extract_items(j):
    res = j.get("result") if isinstance(j, dict) else None
    if not isinstance(res, dict): return []
    items = res.get("items") or []
    return items if isinstance(items, list) else []

def extract_cid_from_item(it):
    cid = it.get("cid")
    if cid: return cid
    u = it.get("URL") or it.get("url") or ""
    m = re.search(r"[?&]id=([a-z0-9_]+)", u, re.I)
    return m.group(1) if m else None

def try_api_latest_cids(limit=60):
    aid, aff = get_api_keys()
    variants = [
        {"site":"FANZA","service":"digital","floor":"videoc"},
        {"site":"FANZA","service":"amateur","floor":"videoc"},
        {"site":None,   "service":"digital","floor":"videoc"},
    ]
    got=[]; seen=set()
    for v in variants:
        for offset in (1,51,101,151,201):
            j = call_itemlist_variant(aid, aff, v["site"], v["service"], v["floor"], offset=offset, hits=50)
            for it in extract_items(j):
                cid = extract_cid_from_item(it)
                if not cid: continue
                if cid not in seen:
                    got.append(cid); seen.add(cid)
                if len(got) >= limit: return got
    return got

def try_html_latest_cids(limit=60):
    url = "https://www.dmm.co.jp/digital/amateur/-/list/=/sort=date/"
    html = urllib.request.urlopen(url, timeout=20).read().decode("utf-8","replace")
    ids = re.findall(r"/amateur/content/\?id=([a-z0_]+)", html, re.I)
    out=[]; seen=set()
    for cid in ids:
        if cid not in seen:
            out.append(cid); seen.add(cid)
        if len(out) >= limit: break
    return out

def load_history():
    if not HIST.exists(): return set()
    return {l.strip() for l in HIST.read_text(encoding="utf-8").splitlines() if l.strip()}

def append_history(cid):
    HIST.parent.mkdir(parents=True, exist_ok=True)
    with HIST.open("a", encoding="utf-8") as f:
        f.write(cid + "\n")

def pick_unseen(cands, history, nth=1):
    unseen = [c for c in cands if c not in history]
    if not unseen: return None
    if nth < 1: nth = 1
    return unseen[nth-1] if len(unseen) >= nth else unseen[-1]

def find_videoc_cid_unique(nth=1):
    history = load_history()
    cands = try_api_latest_cids(limit=max(60, nth))
    if not cands:
        cands = try_html_latest_cids(limit=max(60, nth))
    return pick_unseen(cands, history, nth)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cids", help="CIDをカンマ区切りで指定（例: sweet101,mfcs185）")
    ap.add_argument("--file", help="CIDを1行ずつ列挙したテキストファイル")
    ap.add_argument("--auto", action="store_true", help="自動取得（未処理CIDを優先）")
    ap.add_argument("--auto_index", type=int, default=1, help="自動取得で“n番目の未処理”を選ぶ（既定=1）")
    args = ap.parse_args()

    cids = []
    if not args.cids and not args.file:
        args.auto = True
    if args.cids:
        cids += [c.strip() for c in args.cids.split(",") if c.strip()]
    if args.file:
        cids += [l.strip() for l in Path(args.file).read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.auto:
        cid = find_videoc_cid_unique(args.auto_index)
        if not cid:
            print("[INFO] 未処理の販売中新着が見つからなかったため終了"); sys.exit(0)
        cids = [cid]

    JSONL.parent.mkdir(parents=True, exist_ok=True); JSONL.write_text("", encoding="utf-8")
    CSV.parent.mkdir(parents=True, exist_ok=True);  CSV.exists() and CSV.unlink()

    for cid in list(dict.fromkeys(cids)):
        print(f"[RUN] CID={cid}")
        api   = api_one(cid) or {}
        probe = probe_one(cid)
        raw_samples = samples_one(cid)
        samples = filter_urls(raw_samples, cid)

        enriched = dict(api)  # API優先
        if probe.get("review_body") or probe.get("review") or probe.get("description"):
            enriched["review_body"] = probe.get("review_body") or probe.get("review") or probe.get("description")
        _sizes = probe.get("sizes") or probe.get("sizes_text")
        if _sizes:
            enriched["sizes"] = _sizes
        if probe.get("name") and not enriched.get("performers"):
            enriched["name"] = probe.get("name")
        if probe.get("label") and not enriched.get("series"):
            enriched["label"] = probe.get("label")

        if not enriched.get("sample_images"):
            enriched["sample_images"] = samples
        else:
            enriched["sample_images"] = filter_urls(enriched.get("sample_images") or [], cid)

        merge_and_append(enriched)
        write_csv_row(enriched)
        append_history(cid)
        
        # 🔽 --- GEMINI 追記 --- 🔽
        # データを保存した後、対応する画像をダウンロード
        download_assets_for_post(enriched)
        # 🔼 --- GEMINI 追記 --- 🔼

        print(f"[OK] merged: {cid} images={len(enriched.get('sample_images') or [])} review_len={len((enriched.get('review_body') or ''))}")

    print("[DONE] JSONL:", JSONL, " CSV:", CSV, " HIST:", HIST)


def filter_urls(urls, cid, limit=10):
    import re
    if not urls:
        return []
    norm = [(u or "").split("?",1)[0].split("#",1)[0] for u in urls]
    pat = re.compile(rf"/digital/amateur/{re.escape(cid)}/.*{re.escape(cid)}jp-[0-9]+\.(jpg|jpeg|webp|png)$", re.I)
    out, seen = [], set()
    for base in norm:
        if pat.search(base) and base not in seen:
            out.append(base); seen.add(base)
    return (out[:limit] if out else norm[:limit])


if __name__ == "__main__":
    main()

# ---- postrun archive hook (auto-added) ----
try:
    import sys, subprocess, os
    base_dir = os.path.dirname(__file__)
    arch = os.path.join(base_dir, "scripts", "postrun_archive.py")
    if os.path.exists(arch):
        subprocess.run([sys.executable, arch], check=True)
    else:
        print("[WARN] postrun_archive.py が見つかりません")
except Exception as e:
    print("[WARN] 履歴追記フックで例外:", e)
# ------------------------------------------

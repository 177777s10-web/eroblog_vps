# -*- coding: utf-8 -*-
import argparse, json, os, re, sys, time
from urllib.parse import urlparse
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError
import urllib.request as ur

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"
ALLOW_HOSTS = {"pics.dmm.co.jp","awsimgsrc.dmm.co.jp"}
IMG_RE = re.compile(r"\.(jpg|jpeg|webp|png)(\?.*)?$", re.I)

def norm(u:str)->str:
    if not u: return ""
    u = u.split("?",1)[0].split("#",1)[0]
    return u

def is_allowed_image(u:str)->bool:
    try:
        p = urlparse(u)
        if p.netloc not in ALLOW_HOSTS: return False
        if not IMG_RE.search(p.path):   return False
        return True
    except: return False

def agree_age(page):
    try:
        h1 = (page.locator("h1").first.inner_text(timeout=1200) or "")
    except: h1 = ""
    if "年齢認証" in h1:
        for sel in ["text=同意する","text=はい","text=I Agree"]:
            try:
                btn = page.locator(sel).first
                if btn.count():
                    btn.click(timeout=2000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                    break
            except: pass

def derive_from_og(cid:str, page):
    # og:image 例: https://pics.dmm.co.jp/digital/amateur/bini512/bini512jp.jpg
    try:
        og = page.locator('meta[property="og:image"]').get_attribute("content", timeout=1500) or ""
    except: og = ""
    og = norm(og)
    if not og: return []
    # 連番候補 bini512js-001..010 を生成（パスは og と同じディレクトリ配下）
    # og_dir: /digital/amateur/bini512/
    m = re.search(r"/digital/amateur/([^/]+)/", og)
    if not m: return []
    cid2 = m.group(1)
    if cid2.lower() != cid.lower(): return []
    base_dir = og.rsplit("/",1)[0] + "/"
    out = []
    for i in range(1, 11):
        cand = f"{base_dir}{cid}js-{i:03d}.jpg"
        try:
            req = ur.Request(cand, method="HEAD")
            with ur.urlopen(req, timeout=6) as r:
                if r.status < 400: out.append(cand)
        except: pass
    return out

def collect_images_for_cid(page, cid:str):
    urls = set()
    # ページ内の <img> と <a> を収集
    for sel, attr in [("img","src"), ("a","href")]:
        try:
            els = page.locator(sel)
            n = els.count()
            for i in range(min(n, 2000)):
                try:
                    u = norm(els.nth(i).get_attribute(attr) or "")
                    if not u: continue
                    if not is_allowed_image(u): continue
                    if re.search(rf"/digital/amateur/{re.escape(cid)}/", u, re.I):
                        # js-### のみ採用。jp はポスターなので除外
                        if re.search(rf"/{re.escape(cid)}js-\d+\.(jpg|jpeg|webp|png)$", u, re.I):
                            urls.add(u)
                except: pass
        except: pass
    return sorted(urls)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cid", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--headless", default="true")
    ap.add_argument("--timeout", type=int, default=120000)
    args = ap.parse_args()

    cid = args.cid.strip()
    url = f"https://video.dmm.co.jp/amateur/content/?id={cid}"

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless = (str(args.headless).lower()!="false"))
        ctx = b.new_context(user_agent=UA, storage_state="dmm_storage_state.json" if Path("dmm_storage_state.json").exists() else None)
        page = ctx.new_page()
        page.set_default_timeout(args.timeout)

        page.goto(url, wait_until="domcontentloaded")
        agree_age(page)
        # 遅延読込対策：軽くスクロール
        try:
            for _ in range(8):
                page.mouse.wheel(0, 1200)
                time.sleep(0.2)
        except: pass
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except TimeoutError:
            pass

        imgs = collect_images_for_cid(page, cid)
        if not imgs:
            # フォールバック：og:image から js-### を派生
            imgs = derive_from_og(cid, page)

        out = {
            "cid": cid,
            "url": url,
            "sample_images": imgs,
            "found": len(imgs),
            "notes": [
                f"dom={len(imgs)}",
                f"engine=chromium",
                f"headless={str(args.headless).lower()!='false'}"
            ]
        }

        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, separators=(",",":")), encoding="utf-8")

        ctx.close(); b.close()

if __name__ == "__main__":
    main()

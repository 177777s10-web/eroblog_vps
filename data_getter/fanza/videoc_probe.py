#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FANZA videoc / amateur(content) 詳細ページから
- name / label / sizes / review_body / series
- sample_images（サンプル画像URL配列）
JSON を stdout へ。
使い方:
  python fanza/videoc_probe.py "https://video.dmm.co.jp/amateur/content/?id=sweet101" [--manual] [--save-cookies]
"""
import sys, re, json, time, os, argparse
from urllib.parse import urlparse, parse_qs, unquote
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"
FW2HW = str.maketrans("０１２３４５６７８９", "0123456789")

BWH_RE = re.compile(
    r"(?:B\s*[:：]?\s*([０-９0-9]{2,3})\D+W\s*[:：]?\s*([０-９0-9]{2,3})\D+H\s*[:：]?\s*([０-９0-9]{2,3}))"
    r"|(?:バスト\s*[:：]?\s*([０-９0-9]{2,3}).{0,30}(?:ウエスト|ウェスト)\s*[:：]?\s*([０-９0-9]{2,3}).{0,30}ヒップ\s*[:：]?\s*([０-９0-9]{2,3}))",
    re.I | re.S
)

REVIEW_CANDS = [
    ".d-work__description", ".d-work__body", ".d-work__text", ".d-work__intro",
    ".amateur-detail__txt", ".amateur-detail__description",
    "section#introduction", "section#story", "div#description", "div#introduction",
    ".work-intro", ".work__description", ".intro", ".description", ".c-works__description"
]
EXPAND_BTN = ["button:has-text('もっと見る')","button:has-text('続きを読む')","a:has-text('もっと見る')","a:has-text('続きを読む')"]

def to_half(s:str)->str: return (s or "").translate(FW2HW)

def resolve_url(u:str)->str:
    if not u: return u
    try:
        if "al.fanza.co.jp" in u or "age_check" in u:
            q = parse_qs(urlparse(u).query)
            if "lurl" in q: return unquote(q["lurl"][0])
            if "rurl" in q: return unquote(q["rurl"][0])
    except: pass
    return u

def extract_cid(u:str):
    try:
        q = parse_qs(urlparse(u).query)
        if "id" in q and q["id"][0]: return q["id"][0]
        m = re.search(r"[?&]id=([^&]+)", u)
        if m: return m.group(1)
        path = urlparse(u).path or ""
        m2 = re.search(r"/content/.*?/(\w+)$", path)
        if m2: return m2.group(1)
    except: pass
    return None

def try_inner(page, selector, timeout=900):
    try:
        loc = page.locator(selector).first
        if loc.count() > 0:
            return (loc.inner_text(timeout=timeout) or "").strip()
    except PWTimeout:
        return None
    except:
        return None

def click_if_exists(page, selector, timeout=1200):
    try:
        loc = page.locator(selector).first
        if loc.count() > 0:
            loc.click(timeout=timeout)
            time.sleep(0.25)
            return True
    except:
        return False
    return False

def get_name(page, title_fb:str|None):
    sels = [
        "dt:has-text('名前') + dd", "th:has-text('名前') + td",
        ".d-work__table dt:has-text('名前') + dd",
        ".amateur-detail__table dt:has-text('名前') + dd",
    ]
    for s in sels:
        t = try_inner(page, s)
        if t: return t
    t = title_fb or ""
    t = re.sub(r"^[【\[].*?[】\]]\s*", "", t).strip()
    t = re.sub(r"\s*\|\s*FANZA.*$", "", t).strip()
    return t or None

def get_label(page):
    sels = [
        "dt:has-text('レーベル') + dd", "th:has-text('レーベル') + td",
        ".d-work__table dt:has-text('レーベル') + dd",
        ".amateur-detail__table dt:has-text('レーベル') + dd",
        "a[href*='label=']"
    ]
    for s in sels:
        t = try_inner(page, s)
        if t: return t
    return None

def get_series(page):
    sels = [
        "dt:has-text('シリーズ') + dd", "th:has-text('シリーズ') + td",
        ".d-work__table dt:has-text('シリーズ') + dd",
        ".amateur-detail__table dt:has-text('シリーズ') + dd",
        "a[href*='series=']"
    ]
    for s in sels:
        t = try_inner(page, s)
        if t: return t
    return None

def get_sizes(page):
    T_RE = re.compile(r"(?:T|Ｔ|身長)\s*[:：]?\s*([０-９0-9]{2,3})")
    try:
        selectors = [
            "dt:has-text('サイズ') + dd", "th:has-text('サイズ') + td",
            "li:has-text('サイズ')", ".amateur-detail__table dt:has-text('サイズ') + dd",
        ]
        for sel in selectors:
            try:
                txt = page.locator(sel).first.inner_text(timeout=900) or ""
                txt = txt.strip()
                if not txt: continue
                m = BWH_RE.search(txt)
                if m:
                    g = m.groups()
                    if g[0] and g[1] and g[2]:
                        B,W,H = to_half(g[0]), to_half(g[1]), to_half(g[2])
                    else:
                        B,W,H = to_half(g[3] or ""), to_half(g[4] or ""), to_half(g[5] or "")
                    tm = T_RE.search(txt)
                    if tm:
                        t = to_half(tm.group(1))
                        if t and B and W and H: return f"T{t} B{B} W{W} H{H}"
                    if B and W and H: return f"B{B} W{W} H{H}"
                tm = T_RE.search(txt)
                if tm: return f"T{to_half(tm.group(1))} B-- W-- H--"
            except: pass
    except: pass

    try:
        body = page.locator("body").inner_text(timeout=1500) or ""
    except:
        body = ""

    m = BWH_RE.search(body)
    if m:
        g = m.groups()
        if g[0] and g[1] and g[2]:
            B,W,H = to_half(g[0]), to_half(g[1]), to_half(g[2])
        else:
            B,W,H = to_half(g[3] or ""), to_half(g[4] or ""), to_half(g[5] or "")
        tm = T_RE.search(body)
        if tm:
            t = to_half(tm.group(1))
            if t and B and W and H: return f"T{t} B{B} W{W} H{H}"
        if B and W and H: return f"B{B} W{W} H{H}"

    try:
        for ln in body.splitlines():
            if 'サイズ' in ln or 'T' in ln or '身長' in ln:
                m2 = BWH_RE.search(ln)
                if m2:
                    g = m2.groups()
                    if g[0] and g[1] and g[2]:
                        B,W,H = to_half(g[0]), to_half(g[1]), to_half(g[2])
                    else:
                        B,W,H = to_half(g[3] or ""), to_half(g[4] or ""), to_half(g[5] or "")
                    tm = T_RE.search(ln)
                    if tm:
                        t = to_half(tm.group(1))
                        if t and B and W and H: return f"T{t} B{B} W{W} H{H}"
                    if B and W and H: return f"B{B} W{W} H{H}"
                tm2 = T_RE.search(ln)
                if tm2: return f"T{to_half(tm2.group(1))} B-- W-- H--"
    except: pass

    try:
        scripts = page.locator('script[type="application/ld+json"]').all_inner_texts()
        for sc in scripts or []:
            try:
                data = json.loads(sc)
                txt = ""
                if isinstance(data, list):
                    for d in data:
                        if isinstance(d, dict): txt += (d.get('description') or "") + "\n"
                elif isinstance(data, dict):
                    txt = data.get('description') or ""
                if not txt: continue
                m4 = BWH_RE.search(txt)
                if m4:
                    g = m4.groups()
                    if g[0] and g[1] and g[2]:
                        B,W,H = to_half(g[0]), to_half(g[1]), to_half(g[2])
                    else:
                        B,W,H = to_half(g[3] or ""), to_half(g[4] or ""), to_half(g[5] or "")
                    tm = T_RE.search(txt)
                    if tm:
                        t = to_half(tm.group(1))
                        if t and B and W and H: return f"T{t} B{B} W{W} H{H}"
                    if B and W and H: return f"B{B} W{W} H{H}"
                tm4 = T_RE.search(txt)
                if tm4: return f"T{to_half(tm4.group(1))} B-- W-- H--"
            except: continue
    except: pass

    return "B-- W-- H--"

def _expand_if_any(page):
    try:
        for sel in EXPAND_BTN:
            try: click_if_exists(page, sel)
            except: pass
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3);"); time.sleep(0.25)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);"); time.sleep(0.25)
        except: pass
    except: pass

def _texts_from_selector(page, sel)->str:
    try:
        all_txt = page.locator(sel).all_inner_texts()
        if not all_txt: return ""
        return "\n".join([t.strip() for t in all_txt if t and t.strip()])
    except: return ""

def collect_review(page)->str:
    try:
        for s in ["a:has-text('レビュー')","button:has-text('レビュー')","a[href*='#review']","a[href*='comment']"]:
            click_if_exists(page, s)
    except: pass
    _expand_if_any(page)

    candidates = []
    for s in REVIEW_CANDS:
        t = _texts_from_selector(page, s)
        if t: candidates.append(t)

    try:
        scripts = page.locator('script[type="application/ld+json"]').all_inner_texts()
        for sc in scripts or []:
            try:
                data = json.loads(sc)
                if isinstance(data, list):
                    for d in data:
                        desc = (d or {}).get("description")
                        if isinstance(desc, str) and desc.strip(): candidates.append(desc.strip())
                else:
                    desc = (data or {}).get("description")
                    if isinstance(desc, str) and desc.strip(): candidates.append(desc.strip())
            except: continue
    except: pass

    try:
        og = page.locator('meta[property="og:description"]').first.get_attribute("content")
        if og: candidates.append(og.strip())
    except: pass
    try:
        mdesc = page.locator('meta[name="description"]').first.get_attribute("content")
        if mdesc: candidates.append(mdesc.strip())
    except: pass

    def sanitize(txt):
        lines = []
        for ln in (txt or "").splitlines():
            ln2 = ln.strip()
            if not ln2: continue
            if ln2.startswith("特集") or ln2.startswith("※") or ln2.startswith("MENU"): continue
            lines.append(ln2)
        return "\n".join(lines).strip()

    candidates = [sanitize(c) for c in candidates if c and c.strip()]
    if not candidates: return ""
    return max(candidates, key=lambda t: len(t))[:2000].strip()

def open_sample_tab(page):
    for sel in ["a:has-text('サンプル画像')","button:has-text('サンプル画像')","a:has-text('サンプル')","button:has-text('サンプル')"]:
        if click_if_exists(page, sel): return True
    return False

def lazy_scroll(page, steps=34, pause_ms=420):
    for _ in range(steps):
        page.mouse.wheel(0, 1600)
        page.wait_for_timeout(pause_ms)

def collect_samples(page, timeout_ms):
    imgs = set()
    norm = lambda u: u.split("?")[0].split("#")[0] if u else u

    opened = open_sample_tab(page)
    try:
        page.wait_for_selector("img, picture img", timeout=min(timeout_ms, 25000))
    except PWTimeout:
        pass
    lazy_scroll(page, steps=34, pause_ms=420)
    try:
        page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 15000))
    except: pass

    # DOM
    JS_DOM = """
    () => {
      const urls = new Set();
      const add = (u) => { if (u && /^https?:/.test(u)) urls.add(u.split('?')[0].split('#')[0]); };
      const push = (el) => {
        const c = []; const s = el.getAttribute('src'); if (s) c.push(s);
        const d1 = el.getAttribute('data-src'); if (d1) c.push(d1);
        const d2 = el.getAttribute('data-original'); if (d2) c.push(d2);
        const ss = el.getAttribute('srcset'); if (ss) ss.split(',').forEach(v => c.push(v.trim().split(' ')[0]));
        c.forEach(u => { if (u.includes('pics.dmm.co.jp')) add(u); });
      };
      document.querySelectorAll('img, source, picture img').forEach(push);
      document.querySelectorAll('[style*="background-image"]').forEach(el => {
        const m = /url\\(([^)]+)\\)/i.exec(el.getAttribute('style')||'');
        if (m && m[1]) {
          let u = m[1].replace(/^["']|["']$/g,'');
          if (u.includes('pics.dmm.co.jp')) add(u);
        }
      });
      return [...urls];
    }
    """
    try:
        for u in (page.evaluate(JS_DOM) or []):
            if "pics.dmm.co.jp" in u: imgs.add(norm(u))
    except: pass

    # Network resource
    JS_RES = """
    () => {
      try {
        const list = performance.getEntriesByType('resource')
          .map(e => e.name)
          .filter(u => /^https?:/.test(u) && u.includes('pics.dmm.co.jp'))
          .map(u => u.split('?')[0].split('#')[0]);
        return Array.from(new Set(list));
      } catch(e) { return []; }
    }
    """
    try:
        for u in (page.evaluate(JS_RES) or []):
            if "pics.dmm.co.jp" in u: imgs.add(norm(u))
    except: pass

    # HTML本文から直接抽出（最後の網）
    try:
        html = page.content()
        for m in re.findall(r"https?://[^\"'<>\\s]+pics\\.dmm\\.co\\.jp[^\"'<>\\s]+?jp-\\d+\\.jpg", html, flags=re.I):
            imgs.add(norm(m))
    except: pass

    # それでも0なら og:image から jp-1..10
    if not imgs:
        try:
            og = page.locator('meta[property="og:image"]').first.get_attribute("content")
        except:
            og = None
        if og and "pics.dmm.co.jp" in og:
            base = og.split("?")[0].split("#")[0]
            m = re.sub(r"jp-\\d+\\.jpg$", "jp-{}.jpg", base)
            for i in range(1, 11):
                imgs.add(m.format(i))

    return sorted(imgs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", help="target URL")
    ap.add_argument("--manual", action="store_true")
    ap.add_argument("--save-cookies", action="store_true")
    args = ap.parse_args()

    url = resolve_url(args.url or "")
    cid = extract_cid(url) or ""

    with sync_playwright() as p:
        headless = not args.manual
        browser = p.chromium.launch(headless=headless, args=["--no-sandbox","--disable-dev-shm-usage","--lang=ja-JP"])
        ctx = browser.new_context(user_agent=UA, locale="ja-JP", extra_http_headers={"Referer":"https://video.dmm.co.jp/"})
        try:
            if os.path.exists("cookies.json"):
                ctx.add_cookies(json.load(open("cookies.json","r",encoding="utf-8")))
        except: pass
        try:
            ctx.add_cookies([
                {"name":"ckcy","value":"1","domain":".dmm.co.jp","path":"/"},
                {"name":"age_check_done","value":"1","domain":".dmm.co.jp","path":"/"},
            ])
        except: pass

        page = ctx.new_page()
        try:
            page.goto("https://video.dmm.co.jp/", wait_until="domcontentloaded", timeout=20000)
        except: pass
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
        except:
            try: page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except: pass

        # 年齢認証対応
        try:
            h1 = (page.locator("h1").first.inner_text(timeout=1500) or "")
        except: h1 = ""
        if "年齢認証" in h1:
            for q in ["はい","同意","I Agree"]:
                try:
                    page.get_by_role("link", name=re.compile(q)).first.click(timeout=2000)
                    page.wait_for_load_state("networkidle", timeout=10000)
                    break
                except: pass

        try: title = (page.locator("h1").first.inner_text(timeout=2000) or "").strip()
        except: title = ""

        out = {
            "cid": cid,
            "url_resolved": url,
            "title": title,
            "name": get_name(page, title),
            "label": get_label(page),
            "series": get_series(page),
            "sizes": get_sizes(page),
            "review_body": collect_review(page),
            "sample_images": collect_samples(page, timeout_ms=180000),
        }

        print(json.dumps(out, ensure_ascii=False, indent=2))
        if args.save_cookies:
            try: json.dump(ctx.cookies(), open("cookies.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
            except: pass
        try: ctx.close(); browser.close()
        except: pass

if __name__ == "__main__":
    main()

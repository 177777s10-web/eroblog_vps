# -*- coding: utf-8 -*-
import os, sys, json, re, urllib.parse as up, urllib.request as ur

API_HOST = "https://api.dmm.com/affiliate/v3/ItemList"

def get_api_keys():
    aid = os.environ.get("API_ID") or os.environ.get("DMM_API_ID")
    aff = os.environ.get("AFFILIATE_ID") or os.environ.get("DMM_AFFILIATE_ID")
    if not aid or not aff:
        print("[ERR] API_ID / AFFILIATE_ID が未設定", file=sys.stderr)
        sys.exit(2)
    return aid, aff

def call_itemlist(params):
    url = API_HOST + "?" + up.urlencode(params)
    with ur.urlopen(url, timeout=25) as resp:
        body = resp.read().decode("utf-8", "replace")
    return json.loads(body)

def extract_items(j):
    res = j.get("result") if isinstance(j, dict) else None
    if not isinstance(res, dict):
        return []
    items = res.get("items") or []
    return items if isinstance(items, list) else []

def pick_poster(imageURL):
    if not isinstance(imageURL, dict):
        return None
    for k in ("large","list","small"):
        v = imageURL.get(k)
        if isinstance(v, str) and v:
            return v
    return None

def pick_sample_images(sampleImageURL):
    if not sampleImageURL:
        return []
    imgs = []
    for size_key in ("sample_s","sample","sample_l"):
        blk = sampleImageURL.get(size_key) if isinstance(sampleImageURL, dict) else None
        if isinstance(blk, dict):
            arr = blk.get("image")
            if isinstance(arr, list):
                for x in arr:
                    if isinstance(x, dict):
                        u = x.get("image") or x.get("url")
                        if isinstance(u, str) and u:
                            imgs.append(u)
    if not imgs and isinstance(sampleImageURL, list):
        for x in sampleImageURL:
            if isinstance(x, str) and x:
                imgs.append(x)
    seen=set(); out=[]
    for u in imgs:
        if u not in seen:
            out.append(u); seen.add(u)
    return out

def pick_sample_movie(sampleMovieURL):
    if not isinstance(sampleMovieURL, dict):
        return None
    cand = []
    for v in sampleMovieURL.values():
        if isinstance(v, str) and v.startswith(("http://","https://")):
            cand.append(v)
        elif isinstance(v, dict):
            for vv in v.values():
                if isinstance(vv, str) and vv.startswith(("http://","https://")):
                    cand.append(vv)
    cand_sorted = sorted(cand, key=lambda u: ("1080" in u, "720" in u, "480" in u, "mp4" in u, len(u)), reverse=True)
    return cand_sorted[0] if cand_sorted else None

def normalize_item(it):
    cid = it.get("cid")
    if not cid:
        u = it.get("URL") or it.get("url") or ""
        m = re.search(r"[?&]id=([a-z0-9_]+)", u, re.I)
        cid = m.group(1) if m else None

    title = it.get("title") or ""
    url = it.get("URL") or it.get("url") or ""
    affiliate_url = it.get("affiliateURL") or it.get("affiliate_url") or ""

    poster_url = pick_poster(it.get("imageURL") or it.get("image_url") or {})
    sample_images = pick_sample_images(it.get("sampleImageURL") or it.get("sample_image_url") or {})
    sample_movie_url = pick_sample_movie(it.get("sampleMovieURL") or it.get("sample_movie_url") or {})

    genres, series, maker, performers = [], None, None, []
    info = it.get("iteminfo") or {}
    def names(arr):
        out=[]
        if isinstance(arr, list):
            for x in arr:
                if isinstance(x, dict) and x.get("name"):
                    out.append(x["name"])
        return out
    if isinstance(info, dict):
        genres = names(info.get("genre"))
        ss = names(info.get("series"))
        if ss: series = ss[0]
        mk = names(info.get("maker"))
        if mk: maker = mk[0]
        performers = names(info.get("performer"))

    review_count = it.get("review") or it.get("review_count") or 0
    review_average = it.get("reviewAverage") or it.get("review_average") or None
    date = it.get("date") or it.get("release_date")
    prices = it.get("prices") or {}
    price = prices.get("price") or prices.get("price_download") if isinstance(prices, dict) else None

    return {
        "cid": cid, "title": title,
        "url": url, "affiliate_url": affiliate_url,
        "poster_url": poster_url, "sample_images": sample_images, "sample_movie_url": sample_movie_url,
        "genres": genres, "series": series, "maker": maker, "performers": performers,
        "review_count": review_count, "review_average": review_average,
        "date": date, "price": price, "source": "api",
    }

def search_by_cid(aid, aff, cid, max_pages=5, hits=100):
    # 1) keyword=cid で情報が最も豊富な個体を優先
    variants = [
        {"site":"FANZA","service":"digital"},
        {"site":"FANZA","service":"amateur"},
        {"site":"DMM.com","service":"digital"},
        {"site":None,   "service":"digital"},
    ]
    best = None; best_score = -1
    for v in variants:
        try:
            params = {
                "api_id": aid, "affiliate_id": aff,
                "site": v.get("site"), "service": v.get("service"),
                "floor": "videoc", "sort": "date",
                "hits": hits, "offset": 1, "output": "json",
                "keyword": cid,
            }
            url = API_HOST + "?" + up.urlencode({k:v for k,v in params.items() if v})
            with ur.urlopen(url, timeout=20) as resp:
                j = json.loads(resp.read().decode("utf-8","replace"))
        except Exception:
            continue
        for it in extract_items(j):
            cand = it.get("cid")
            if not cand:
                u = it.get("URL") or it.get("url") or ""
                m = re.search(r"[?&]id=([a-z0-9_]+)", u, re.I)
                cand = m.group(1) if m else None
            if not cand or cand.lower() != cid.lower():
                continue
            info = it.get("iteminfo") or {}
            genres = info.get("genre") or []
            img = it.get("sampleImageURL")
            mov = it.get("sampleMovieURL")
            imgl = (it.get("imageURL") or {}).get("large")
            score = (len(genres) if isinstance(genres, list) else 0) + bool(img) + bool(mov) + bool(imgl)
            if score > best_score:
                best = it; best_score = score
    if best:
        return normalize_item(best)

    # 2) 見つからなければ従来の走査
    for page in range(max_pages):
        offset = page * hits + 1
        params = {
            "api_id": aid, "affiliate_id": aff,
            "site": "FANZA", "service": "digital",
            "floor": "videoc", "sort": "date",
            "hits": hits, "offset": offset, "output": "json",
        }
        j = call_itemlist(params)
        items = extract_items(j)
        if not items:
            break
        for it in items:
            cand = it.get("cid")
            if not cand:
                u = it.get("URL") or it.get("url") or ""
                m = re.search(r"[?&]id=([a-z0-9_]+)", u, re.I)
                cand = m.group(1) if m else None
            if cand and cand.lower() == cid.lower():
                return normalize_item(it)
    return None

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cid", required=True)
    args = ap.parse_args()
    aid, aff = get_api_keys()
    d = search_by_cid(aid, aff, args.cid)
    if not d:
        print(json.dumps({"error":"not_found","cid":args.cid}, ensure_ascii=False)); sys.exit(0)
    print(json.dumps(d, ensure_ascii=False))

if __name__ == "__main__":
    main()

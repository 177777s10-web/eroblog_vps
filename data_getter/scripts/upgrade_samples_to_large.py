#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re, sys, urllib.request as ur, urllib.error as ue, time
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"

def probe(url: str, timeout=8) -> bool:
    try:
        req = ur.Request(url, headers={"User-Agent": UA})
        with ur.urlopen(req, timeout=timeout) as r:
            code = getattr(r, "status", 200)
            return 200 <= code < 400
    except Exception:
        return False

def prefer_large(url: str, cid: str) -> str:
    base = url.split("?",1)[0].split("#",1)[0]
    cand = re.sub(r'/([A-Za-z0-9_]+)js-([0-9]+)\.(jpg|jpeg|webp|png)$', r'/\1jp-\2.\3', base)
    cand = re.sub(rf'/(?:{re.escape(cid)})jm\.(jpg|jpeg|webp|png)$', rf'/{cid}jp.\1', cand)
    if cand != base and probe(cand):
        return cand
    return base

def main(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cid = data.get("cid") or ""
    imgs = data.get("sample_images") or []
    out = []
    seen = set()
    for u in imgs:
        v = prefer_large(u or "", cid)
        if v and v not in seen:
            out.append(v); seen.add(v)
    data["sample_images"] = out
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"upgraded: {path}  images={len(out)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: upgrade_samples_to_large.py <samples.json>", file=sys.stderr); sys.exit(2)
    main(sys.argv[1])

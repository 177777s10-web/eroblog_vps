# -*- coding: utf-8 -*-
import subprocess, re
from urllib.parse import urlparse

ALLOW_HOSTS = ("pics.dmm.co.jp","awsimgsrc.dmm.co.jp")
EXTS = (".jpg",".jpeg",".webp",".png")

def run_cmd(cmd: str) -> str:
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed: {cmd}\n{p.stderr}")
    return p.stdout

def filter_sample_urls(urls, cid):
    pat_path = re.compile(rf"/amateur/{re.escape(cid)}/", re.I)
    pat_name = re.compile(rf"/{re.escape(cid)}(js|jp)-\d+\.(jpg|jpeg|webp|png)$", re.I)
    kept = []
    for u in urls or []:
        u = (u or "").split("?")[0].split("#")[0]
        if not u:
            continue
        try:
            pr = urlparse(u)
            if pr.netloc.endswith(ALLOW_HOSTS) and u.lower().endswith(EXTS) and (pat_path.search(pr.path) or pat_name.search(pr.path)):
                kept.append(u)
        except:
            pass
    if not kept:
        base = f"https://awsimgsrc.dmm.co.jp/pics_dig/digital/amateur/{cid}/{cid}js-"
        kept = [f"{base}{i:03d}.jpg" for i in range(1,11)]
    out, seen = [], set()
    for u in kept:
        if u not in seen:
            out.append(u); seen.add(u)
    return out

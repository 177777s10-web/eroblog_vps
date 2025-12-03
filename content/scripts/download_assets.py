#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, urllib.request
from pathlib import Path
import time

# --- 設定 ---
EXPORTS = Path.home()/ "eroblog"/ "content"/ "exports"/ "latest.jsonl"
ASSETS  = Path.home()/ "eroblog"/ "content"/ "assets"
# ---

ASSETS.mkdir(parents=True, exist_ok=True)

# [修正] 偽装ヘッダー (自分をブラウザだと偽る)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'Referer': 'https://www.dmm.co.jp/'
}

def download_file(url, dest_path):
    """ 偽装ヘッダー付きでファイルをダウンロードする """
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as response:
            with open(dest_path, 'wb') as out_file:
                out_file.write(response.read())
        return True
    except Exception as e:
        print(f"  └ Failed: {e}")
        return False

try:
    with EXPORTS.open(encoding="utf-8") as f:
        line = f.readline()
    if not line: print("エラー: latest.jsonl が空です。"); exit()
            
    data = json.loads(line)
    cid = data.get("cid")
    if not cid: print("エラー: 1行目から cid が見つかりません。"); exit()

    print(f"--- 処理対象: {cid} ---")

    # poster_urlを {cid}_poster.jpg として保存
    poster_url = data.get("poster_url")
    if poster_url:
        poster_ext = (os.path.splitext(poster_url)[1] or ".jpg").split('?')[0]
        poster_dest = ASSETS / f"{cid}_poster{poster_ext}"
        
        if not poster_dest.exists():
            large_poster_url = poster_url.replace("jm.jpg", "pl.jpg")
            print(f"Downloading large poster: {large_poster_url}")
            if not download_file(large_poster_url, poster_dest):
                print(f"Falling back to original: {poster_url}")
                if not download_file(poster_url, poster_dest):
                    print(f"skip poster: {poster_url}")
            if poster_dest.exists(): print(f"saved poster: {poster_dest.name}")
        else:
            print(f"exists poster: {poster_dest.name}")

    # sample_imagesを {cid}_{num}.jpg として保存
    for j, u in enumerate(data.get("sample_images") or []):
        ext = (os.path.splitext(u)[1] or ".jpg").split('?')[0]
        dest = ASSETS / f"{cid}_{j+1:02d}{ext}"
        if not dest.exists():
            print(f"Downloading sample: {u}")
            if download_file(u, dest):
                print(f"saved sample: {dest.name}")
        else:
            print(f"exists sample: {dest.name}")
            
    print("------------------------")

except Exception as e:
    print(f"スクリプト実行中にエラーが発生しました: {e}")

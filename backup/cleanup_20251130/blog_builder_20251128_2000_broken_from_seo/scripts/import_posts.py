import os
import sys
import json
from pathlib import Path
from datetime import datetime

import django
import frontmatter
from django.utils import timezone

# --- Django 初期化 ---
SCRIPT_DIR   = Path(__file__).resolve().parent      # .../blog_builder/scripts
PROJECT_ROOT = SCRIPT_DIR.parent                    # .../blog_builder
BASE_DIR     = PROJECT_ROOT.parent                  # .../eroblog

sys.path.append(str(BASE_DIR))
sys.path.append(str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog_builder.settings")
django.setup()

from posts.models import Post  # noqa

QUEUE_DIR     = BASE_DIR / "publish_queue"
CONTENT_ROOT  = BASE_DIR / "content"
PUBLISHED_DIR = CONTENT_ROOT / "published"
PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)


def extract_review(text: str) -> str:
    """
    Markdown 本文から『## 紹介文（レビュー）』以降だけを抜き出す。
    マーカーが無い場合は全文。
    """
    marker = "## 紹介文（レビュー）"
    if marker in text:
        text = text.split(marker, 1)[1]
    return text.strip()


def first_meta(meta, keys, default=""):
    """frontmatter の複数キー候補から最初に見つかった値を返す"""
    for k in keys:
        v = meta.get(k)
        if v not in (None, ""):
            return v
    return default


def parse_release_date(meta):
    s = first_meta(meta, ["release_date", "配信開始日", "date"], "")
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_default_timezone())
            return dt
        except Exception:
            continue
    return None


def main():
    queue_files = sorted(QUEUE_DIR.glob("*.json"))
    if not queue_files:
        print("INFO: publish_queue に処理待ちがありません。")
        return

    for q in queue_files:
        cid = q.stem
        print(f"--- Processing CID: {cid} ---")

        try:
            with q.open("r", encoding="utf-8") as f:
                qdata = json.load(f)
            draft_rel = qdata.get("draft_path")
            if not draft_rel:
                print(f"FAIL: {q.name} に draft_path がないのでスキップ")
                continue

            md_path = BASE_DIR / draft_rel
            if not md_path.exists():
                print(f"FAIL: 原稿 {md_path} が見つからないのでスキップ")
                continue

            post_data = frontmatter.load(md_path)
            meta = post_data.metadata

            try:
                post = Post.objects.get(cid=cid)
            except Post.DoesNotExist:
                print(f"FAIL: DB に cid={cid} がないのでスキップ")
                continue

            # レビュー本文
            review_body = extract_review(post_data.content)
            post.review_body = review_body
            # 旧フィールドを使っているテンプレ対策として同じ内容をコピー
            if hasattr(post, "review"):
                post.review = review_body

            # サイズ（あれば更新／無ければそのまま）
            size_str = first_meta(meta, ["サイズ", "size", "sizes"], "")
            if size_str:
                post.sizes = size_str  # T入りの文字列ごと保存

            # 画像・URL・名前など（frontmatter にあれば更新）
            aff = first_meta(meta, ["アフィリエイトURL", "affiliate_url"], "")
            if aff:
                post.affiliate_url = aff

            smv = first_meta(meta, ["サンプル動画", "sample_movie_url"], "")
            if smv:
                post.sample_movie_url = smv

            name = first_meta(meta, ["出演者", "name"], "")
            if name:
                post.name = name

            maker = first_meta(meta, ["メーカー", "maker"], "")
            if maker:
                post.maker = maker  # 空文字にはしない

            label = first_meta(meta, ["レーベル", "label"], "")
            if label:
                post.label = label

            tags = meta.get("tags")
            if tags is not None:
                if not isinstance(tags, list):
                    tags = [str(tags)]
                post.genres = tags

            if not post.release_date:
                rd = parse_release_date(meta)
                if rd:
                    post.release_date = rd

            post.draft_path = str(PUBLISHED_DIR / md_path.name)
            post.save()

            # 原稿移動 & queue 削除
            published_path = PUBLISHED_DIR / md_path.name
            if published_path.exists():
                published_path.unlink()
            md_path.rename(published_path)
            q.unlink()

            print(f"SUCCESS: [{cid}] を DB に更新しました。sizes={post.sizes!r}")

        except Exception as e:
            print(f"FATAL: [{cid}] の処理でエラー: {e}")
            print("FATAL: この CID はスキップします。")


if __name__ == "__main__":
    main()

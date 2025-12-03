from django.shortcuts import render, get_object_or_404
from django.utils.html import mark_safe
from django.urls import reverse
from django.core.paginator import Paginator
from .models import Post
import itertools
import random
import markdown

GENRE_OMIT = {
    "ハイビジョン", "HD", "4K", "独占配信",
    "動画", "サンプル動画", "素人", "素人ハメ撮り",
    "FANZA",
}


def _to_list(genres):
    if isinstance(genres, list):
        return [g for g in genres if isinstance(g, str)]
    if isinstance(genres, str):
        return [g.strip() for g in genres.split('/') if g.strip()] \
            or [g.strip() for g in genres.split('、') if g.strip()] \
            or [g.strip() for g in genres.split(',') if g.strip()]
    return []


def _build_genre_pairs(post):
    tags = [t for t in _to_list(post.genres) if t and t not in GENRE_OMIT]

    # 重複ジャンルを順序維持で除去
    uniq = []
    for t in tags:
        if t not in uniq:
            uniq.append(t)
    tags = uniq

    pairs = []
    used = set()
    seen_labels = set()

    # 1周目: キーワードが被らない組み合わせを優先して選ぶ
    for a, b in itertools.combinations(tags, 2):
        if a == b:
            continue
        label = f"{a}×{b}"
        if label in seen_labels:
            continue
        if a in used or b in used:
            continue
        pairs.append({"main": a, "with": b, "label": label})
        used.add(a)
        used.add(b)
        seen_labels.add(label)
        if len(pairs) >= 3:
            break

    # 2周目: まだ3個に満たない場合、被りOKで追加
    if len(pairs) < 3:
        for a, b in itertools.combinations(tags, 2):
            if a == b:
                continue
            label = f"{a}×{b}"
            if label in seen_labels:
                continue
            pairs.append({"main": a, "with": b, "label": label})
            seen_labels.add(label)
            if len(pairs) >= 3:
                break

    return pairs


def build_review_excerpt(post, length: int = 60) -> str:
    """
    トップページのカード用に、レビュー本文だけを短く1行抜き出す。
    先頭の「# 名前 ## 基本情報 ## レビュー」行はここで捨てる。
    """
    raw = (
        getattr(post, "review", None)
        or getattr(post, "review_body", None)
        or ""
    )
    raw = str(raw).strip()
    if not raw:
        return ""

    import re as _re

    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        # 見出し行（# で始まる）は捨てる
        if s.startswith("#"):
            continue
        # 「基本情報」「レビュー」「Profile」などメタ情報っぽい行も捨てる
        if any(w in s for w in ("基本情報", "レビュー", "Profile", "プロフィール")):
            continue
        lines.append(s)

    if not lines:
        # 全部メタ情報だった場合は、元のテキストを1行に潰して使う
        text = " ".join(raw.split())
    else:
        # 最初の本文行だけを使う
        text = lines[0]

    # Markdown の記号をざっくり削除
    text = _re.sub(r"[#*_`>]+", "", text)
    text = " ".join(text.split())

    return text[:length]


def post_index(request):
    qs = Post.objects.all().order_by("-release_date", "-id")
    paginator = Paginator(qs, 30)

    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    # カード用の抜粋文をここで作っておく
    for p in page_obj.object_list:
        p.review_excerpt = build_review_excerpt(p, length=120)

    return render(request, "post_index.html", {
        "posts": list(page_obj.object_list),
        "page_obj": page_obj,
    })



def post_detail(request, cid):
    post = get_object_or_404(Post, cid=cid)

    raw_review = (post.review or post.review_body or "").strip()
    if raw_review:
        body_html = mark_safe(
            markdown.markdown(raw_review, extensions=["extra"])
        )
    else:
        body_html = ""

    # サイズ表示用（Tが含まれていればそのまま出す）
    if getattr(post, "sizes", None):
        seo_sizes = post.sizes
    elif post.bust and post.waist and post.hip:
        seo_sizes = f"B{post.bust} W{post.waist} H{post.hip}"
    else:
        seo_sizes = ""

    actress_label = post.name or post.title or post.cid

    base = "/media"
    sample_images = [f"{base}/{post.cid}_{i:02d}.jpg" for i in range(1, 6)]
    poster_url = f"{base}/{post.cid}_poster.jpg"

    if raw_review:
        one_line = "".join(raw_review.splitlines())
        meta_description = one_line[:120]
    else:
        meta_description = f"{actress_label} の素人ハメ撮り作品レビューです。"

    page_url = request.build_absolute_uri(
        reverse("post_detail", kwargs={"cid": post.cid})
    )

    genre_pairs = _build_genre_pairs(post)
    genre_text_list = _to_list(post.genres)
    genre_text = " / ".join(genre_text_list) if genre_text_list else ""

    # ① 同じメーカー：最大9件（3×3）
    same_maker_posts = Post.objects.filter(
        maker=post.maker
    ).exclude(
        id=post.id
    ).order_by("-release_date", "-id")[:9]

    # ② 人気記事：6件（3×2） ※メーカー問わず
    popular_posts = Post.objects.exclude(
        id=post.id
    ).order_by("-release_date", "-id")[:6]

    # ③ 他メーカー：メーカーごとに最大6件（3×2）を複数メーカー分
    others_qs = Post.objects.exclude(id=post.id)
    if post.maker:
        others_qs = others_qs.exclude(maker=post.maker)

    others = list(others_qs.order_by("-release_date", "-id")[:200])
    random.shuffle(others)

    maker_map = {}
    for p2 in others:
        maker = (p2.maker or "").strip()
        if not maker:
            continue
        lst = maker_map.setdefault(maker, [])
        if len(lst) < 6:   # 3列×2段
            lst.append(p2)

    other_maker_blocks = []
    for maker, posts_for_maker in maker_map.items():
        if posts_for_maker:
            other_maker_blocks.append({
                "maker": maker,
                "posts": posts_for_maker,
            })
        if len(other_maker_blocks) >= 3:
            break

    context = {
        "post": post,
        "body_html": body_html,
        "seo_sizes": seo_sizes,
        "actress_label": actress_label,
        "poster_url": poster_url,
        "sample_images": sample_images,
        "meta_description": meta_description,
        "page_url": page_url,
        "genre_pairs": genre_pairs,
        "genre_text": genre_text,
        "same_maker_posts": same_maker_posts,
        "popular_posts": popular_posts,
        "other_maker_blocks": other_maker_blocks,
    }
    # 詳細ページのレビューは今まで通り HTML から抜粋・・・
    context["review_excerpt"] = build_review_excerpt_html(body_html)
    return render(request, "post_detail_template.html", context)


def genre_list(request, main):
    qs = Post.objects.all().order_by("-release_date", "-id")
    filtered = [p for p in qs if main in _to_list(p.genres)]

    for p in filtered:
        p.review_excerpt = build_review_excerpt(p, length=120)

    return render(request, "post_index.html", {
        "posts": filtered,
        "genre_main": main,
        "page_obj": None,
    })


def build_review_excerpt_html(body_html: str, length: int = 250) -> str:
    """body_html からレビュー本文の抜粋を取り出す（詳細ページ用）"""
    if not body_html:
        return ""
    import re as _re, html as _html
    # 「レビュー」見出し直後の <p>...</p> を優先して取る
    m = _re.search(r"<h2>レビュー</h2>\s*<p>(.*?)</p>", body_html, _re.S)
    if m:
        text_html = m.group(1)
    else:
        m2 = _re.search(r"<p>(.*?)</p>", body_html, _re.S)
        text_html = m2.group(1) if m2 else body_html
    # タグ除去と整形
    text = _re.sub(r"<[^>]+>", "", text_html)
    text = _html.unescape(text)
    text = " ".join(text.split())
    return text[:length]



# AUTO_PATCH_PAGINATION
from django.core.paginator import Paginator

def post_index(request):
    qs = Post.objects.all().order_by("-release_date", "-id")
    paginator = Paginator(qs, 30)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    # 一覧カード用のレビュー1行抜粋を準備
    for p in page_obj:
        p.review_excerpt = build_review_excerpt(p, length=120)

    for p in page_obj:
        p.review_excerpt = build_review_excerpt(p, length=120)

    return render(request, "post_index.html", {
        "posts": page_obj,
        "page_obj": page_obj,
    })

def genre_list(request, main):
    qs = Post.objects.all().order_by("-release_date", "-id")
    filtered = [p for p in qs if main in _to_list(p.genres)]
    for p in filtered:
        p.review_excerpt = build_review_excerpt(p, length=120)
    return render(request, "post_index.html", {
        "posts": filtered,
        "genre_main": main,
    })

from django.shortcuts import render, get_object_or_404
from django.utils.html import mark_safe
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import F
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

    uniq = []
    for t in tags:
        if t not in uniq:
            uniq.append(t)
    tags = uniq

    pairs = []
    used = set()
    seen_labels = set()

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
        if s.startswith("#"):
            continue
        if any(w in s for w in ("基本情報", "レビュー", "Profile", "プロフィール")):
            continue
        lines.append(s)

    if not lines:
        text = " ".join(raw.split())
    else:
        text = lines[0]

    text = _re.sub(r"[#*_`>]+", "", text)
    text = " ".join(text.split())
    return text[:length]


def build_review_excerpt_html(body_html: str, length: int = 250) -> str:
    if not body_html:
        return ""
    import re as _re, html as _html
    m = _re.search(r"<h2>レビュー</h2>\s*<p>(.*?)</p>", body_html, _re.S)
    if m:
        text_html = m.group(1)
    else:
        m2 = _re.search(r"<p>(.*?)</p>", body_html, _re.S)
        text_html = m2.group(1) if m2 else body_html
    text = _re.sub(r"<[^>]+>", "", text_html)
    text = _html.unescape(text)
    text = " ".join(text.split())
    return text[:length]


def post_index(request):
    qs = Post.objects.order_by("-release_date", "-id")

    query = (request.GET.get("q") or "").strip()
    if query:
        qs = qs.filter(title__icontains=query)

    paginator = Paginator(qs, 30)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    for p in page_obj:
        p.review_excerpt = build_review_excerpt(p, length=120)

    popular_posts = Post.objects.order_by("-view_total", "-id")[:30]

    context = {
        "page_obj": page_obj,
        "posts": page_obj.object_list,
        "popular_posts": popular_posts,
        "genre_main": None,
        "query": query,
    }
    return render(request, "post_index.html", context)


def post_detail(request, cid):
    post = get_object_or_404(Post, cid=cid)

    if hasattr(post, "view_total"):
        Post.objects.filter(pk=post.pk).update(view_total=F("view_total") + 1)
        post.refresh_from_db()

    raw_review = (post.review or post.review_body or "").strip()
    if raw_review:
        body_html = mark_safe(
            markdown.markdown(raw_review, extensions=["extra"])
        )
    else:
        body_html = ""

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

    same_maker_posts = Post.objects.filter(
        maker=post.maker
    ).exclude(
        id=post.id
    ).order_by("-release_date", "-id")[:9]

    popular_posts = Post.objects.exclude(
        id=post.id
    ).order_by("-release_date", "-id")[:6]

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
        if len(lst) < 6:
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
    context["review_excerpt"] = build_review_excerpt_html(body_html)
    return render(request, "post_detail_template.html", context)


def genre_list(request, main):
    base_qs = Post.objects.order_by("-release_date", "-id")
    filtered = [p for p in base_qs if main in _to_list(p.genres)]

    paginator = Paginator(filtered, 30)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    for p in page_obj:
        p.review_excerpt = build_review_excerpt(p, length=120)

    popular_posts = Post.objects.order_by("-view_total", "-id")[:30]

    return render(request, "post_index.html", {
        "page_obj": page_obj,
        "posts": page_obj.object_list,
        "popular_posts": popular_posts,
        "genre_main": main,
        "query": "",
    })


def contact(request):
    return render(request, "contact.html", {})


def privacy(request):
    return render(request, "privacy.html", {})

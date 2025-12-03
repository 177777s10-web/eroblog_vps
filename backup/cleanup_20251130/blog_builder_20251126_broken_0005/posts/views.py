from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Post




def post_index(request):
    """
    トップページ
    左：CID の新しい順（最新順）
    右：全体の閲覧数トップ10
    """
    from django.core.paginator import Paginator
    from .models import Post

    # 左カラム：CID の新しい順（最新から）
    post_list = Post.objects.order_by("-cid")
    paginator = Paginator(post_list, 24)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # 右カラム：全体の閲覧数トップ10
    popular_posts = Post.objects.order_by("-view_count", "-id")[:10]

    return render(
        request,
        "post_index.html",
        {
            "posts": page_obj,               # 左のカード（最新順）
            "page_obj": page_obj,            # ページャー
            "popular_posts": popular_posts,  # 右カラム（閲覧数トップ10）
            "genre_main": None,
        },
    )

def post_detail(request, cid):
    """
    記事詳細:
    表示ごとに view_count を +1
    """
    post = get_object_or_404(Post, cid=cid)

    if getattr(post, "view_count", None) is None:
        post.view_count = 0
    Post.objects.filter(pk=post.pk).update(view_count=post.view_count + 1)
    post.refresh_from_db()

    return render(request, "posts/post_detail.html", {"post": post})


def genre_list(request, main, sub=None):
    """
    ジャンル別一覧:
    左: CID の降順
    右: サイト全体の人気10件
    """
    qs = Post.objects.all()
    if main:
        qs = qs.filter(genres__icontains=main)
    if sub:
        qs = qs.filter(genres__icontains=sub)

    qs = qs.order_by("-cid")

    paginator = Paginator(qs, 24)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    posts = page_obj.object_list

    popular_posts = Post.objects.order_by("-view_count", "-cid")[:10]

    context = {
        "posts": posts,
        "page_obj": page_obj,
        "popular_posts": popular_posts,
        "genre_main": main,
        "genre_sub": sub,
    }
    return render(request, "post_index.html", context)

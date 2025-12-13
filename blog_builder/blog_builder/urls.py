from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from posts import views as post_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # 一覧（トップ）
    path("", post_views.post_index, name="post_index"),

    # 互換：/posts/ でも一覧を出す（パンくずの「トップ」がここを指しても死なないように）
    path("posts/", post_views.post_index, name="posts_index"),

    # 固定ページなど
    path("genre/<str:main>/", post_views.genre_list, name="genre_list"),
    path("contact/", post_views.contact, name="contact"),
    path("privacy/", post_views.privacy, name="privacy"),

    # 詳細：/posts/<cid>/
    path("posts/<str:cid>/", post_views.post_detail, name="post_detail"),

    # 互換：/ <cid> /（既存リンクが残ってても動くように）
    path("<str:cid>/", post_views.post_detail, name="post_detail_legacy"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

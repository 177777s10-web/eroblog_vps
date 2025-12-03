from django.contrib import admin
from django.urls import path
from posts.views import post_detail, post_index
from django.conf import settings
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.static import static

# 1. さっき作った 'posts' アプリの views.py を読み込む
from posts import views as post_views

urlpatterns = [
    path('genre/<str:main>/', post_views.genre_list, name='genre_list'),
    path('posts/', post_index, name='post_index'),
    path('admin/', admin.site.urls),
    
    # 2. 「記事」ページのURL（住所）を登録する
    # 例: /posts/himemix420/ というURLにアクセスが来たら、
    # 'posts/views.py' の中の 'post_detail_view' 関数を呼び出す
    path('posts/<str:cid>/', post_views.post_detail, name='post_detail'),
]

# --- ▼ Geminiによる追記（開発中の画像表示に必須） ---
# 3. /media/ 以下の画像ファイル（.../assets/）を配信できるようにする設定
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# --- ▲ 追記ここまで ---

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


from django.conf import settings
from django.conf.urls.static import static
from pathlib import Path as _Path

_ASSETS_ROOT = _Path(__file__).resolve().parent.parent.parent / "content" / "assets"

if settings.DEBUG:
    urlpatterns += static("/assets/", document_root=_ASSETS_ROOT)

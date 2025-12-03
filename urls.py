from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from posts.sitemaps import PostSitemap
from django.urls import path, include
from django.views.generic import TemplateView
from posts.admin_views import template_body

urlpatterns = [

    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),

    path('', include('posts.urls')),

    path('admin/posts/template_body/', template_body, name='admin_template_body'),
    path('admin/', admin.site.urls),
]


sitemaps = {
    'posts': PostSitemap,
}

urlpatterns += [
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]

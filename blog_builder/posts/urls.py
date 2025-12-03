from django.urls import path
from .views import (
    post_index,
    post_detail,
    genre_list,
    contact,
    privacy,
)

urlpatterns = [
    # /posts/
    path("", post_index, name="post_index"),

    # /posts/genre/○○/
    path("genre/<str:main>/", genre_list, name="genre_list"),

    # /posts/contact/
    path("contact/", contact, name="contact"),

    # /posts/privacy/
    path("privacy/", privacy, name="privacy"),

    # /posts/<cid>/
    path("<str:cid>/", post_detail, name="post_detail"),
]

from django.conf.urls import include
from django.contrib import admin
from django.urls import re_path

urlpatterns = [
    re_path(r"^users/", include("smartmin.users.urls")),
    re_path(r"^blog/", include("test_runner.blog.urls")),
    re_path(r"^admin/", admin.site.urls),
]

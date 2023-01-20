from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.urls import re_path

from .views import Login, UserCRUDL

logout_url = getattr(settings, "LOGOUT_REDIRECT_URL", None)

urlpatterns = [
    re_path(r"^login/$", Login.as_view(), dict(template_name="smartmin/users/login.html"), name="users.user_login"),
    re_path(
        r"^logout/$",
        LogoutView.as_view(),
        dict(redirect_field_name="go", next_page=logout_url),
        name="users.user_logout",
    ),
]

urlpatterns += UserCRUDL().as_urlpatterns()

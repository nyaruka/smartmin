from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import patterns, url
from django.contrib.auth.views import logout
from .views import login, UserCRUDL

logout_url = getattr(settings, 'LOGOUT_REDIRECT_URL', None)

urlpatterns = patterns('',
    url(r'^login/$', login, dict(template_name='smartmin/users/login.html'), name="users.user_login"),
    url(r'^logout/$', logout, dict(redirect_field_name='go', next_page=logout_url), name="users.user_logout"),        
)

urlpatterns += UserCRUDL().as_urlpatterns()

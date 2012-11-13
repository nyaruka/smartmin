from django.conf.urls.defaults import *

from .views import *
from django.contrib.auth.views import login, logout
from django.conf import settings

logout_url = getattr(settings, 'LOGOUT_REDIRECT_URL', None)
recovery = UserCRUDL().view_for_action('recover').as_view()

urlpatterns = patterns('',
    url(r'^login/$', login, dict(template_name='smartmin/users/login.html'), name="users.user_login"),
    url(r'^logout/$', logout, dict(redirect_field_name='go', next_page=logout_url), name="users.user_logout"),        
)

urlpatterns += UserCRUDL().as_urlpatterns()
urlpatterns += patterns('/^users/', url(r'/recover/(?P<token>\w+)/$', recovery, name='users.user_recover'),)




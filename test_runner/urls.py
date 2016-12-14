from __future__ import unicode_literals

from django.conf.urls import include, url
from django.contrib import admin


urlpatterns = [
    url(r'^users/', include('smartmin.users.urls')),
    url(r'^blog/', include('test_runner.blog.urls')),
    url(r'^csv_imports/', include('smartmin.csv_imports.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
]

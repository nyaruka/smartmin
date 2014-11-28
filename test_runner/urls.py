from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'proj.views.home', name='home'),

    url(r'^users/', include('smartmin.users.urls')),
    url(r'^blog/', include('test_runner.blog.urls')),
    url(r'^csv_imports/', include('smartmin.csv_imports.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

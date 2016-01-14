from __future__ import absolute_import, unicode_literals

from smartmin.csv_imports.views import ImportTaskCRUDL

urlpatterns = ImportTaskCRUDL().as_urlpatterns()

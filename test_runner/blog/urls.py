from __future__ import absolute_import, unicode_literals

from .views import *

urlpatterns = PostCRUDL().as_urlpatterns()
urlpatterns += CategoryCRUDL().as_urlpatterns()
urlpatterns += UserCRUDL().as_urlpatterns()

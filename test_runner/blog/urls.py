from __future__ import unicode_literals

from .views import PostCRUDL, CategoryCRUDL, UserCRUDL

urlpatterns = PostCRUDL().as_urlpatterns()
urlpatterns += CategoryCRUDL().as_urlpatterns()
urlpatterns += UserCRUDL().as_urlpatterns()

from .views import CategoryCRUDL, PostCRUDL, UserCRUDL

urlpatterns = PostCRUDL().as_urlpatterns()
urlpatterns += CategoryCRUDL().as_urlpatterns()
urlpatterns += UserCRUDL().as_urlpatterns()

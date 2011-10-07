from smartmin.views import *
from .models import *

class PostCRUDL(SmartCRUDL):
    model = Post
    permissions = True

    class List(SmartListView):
        fields = ('title', 'tags', 'created_by')
        search_fields = ('title__icontains', 'body__icontains')
        default_order = 'title'

        def get_body(self, obj):
            if len(obj.body) < 100:
                return obj.body
            else:
                return " ".join(obj.body.split(" ")[0:10]) + ".."

    class Update(SmartUpdateView):
        success_message = "Your blog post has been updated."


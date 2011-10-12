
from smartmin.views import *
from .models import *

class PostCRUDL(SmartCRUDL):
    model = Post
    permissions = True
    actions = ('create', 'read', 'update', 'delete', 'list', 'author')

    class List(SmartListView):
        fields = ('title', 'tags', 'created_on', 'created_by')
        search_fields = ('title__icontains', 'body__icontains')
        default_order = 'title'

    class Author(SmartListView):
        fields = ('title', 'tags', 'created_on', 'created_by')
        default_order = ('created_by__username', 'order')

    class Update(SmartUpdateView):
        success_message = "Your blog post has been updated."

    class Create(SmartCreateView):
        submit_button_name = "Create New Post"


SmartReadView
==================

The SmartReadView provides a simple readonly view of your object.  This is essentially just a detail view.

**fields**

Defines which fields should be displayed for the object, and in what order::

  class PostCRUDL(SmartCRUDL):
    model = Post

    class Read(SmartReadView):
        fields = ('title', 'tags', 'body')

Note that if you'd like to have this be set at runtime, you can do so by overriding the ``derive_fields`` method.

**permission**

Let's you set what permission the user must have in order to view this page.

**template_name**

The name of the template used to render this view.  By default, this is set to ``smartmin/create.html`` but you can override it to whatever you'd like.


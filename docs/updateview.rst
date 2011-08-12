SmartUpdateView
==================

The SmartUpdateView provides a simple and quick way to create form pages for updating objects.  The following attributes are available.

**fields**

Defines which fields should be displayed in our form, and in what order::

  class PostCRUDL(SmartCRUDL):
    model = Post

    class Update(SmartUpdateView):
        fields = ('title', 'tags', 'body')

Note that if you'd like to have this be set at runtime, you can do so by overriding the ``derive_fields`` method.

**readonly**

A tuple of field names for fields which should be displayed in the form, but which should be not be editable::

  class PostCRUDL(SmartCRUDL):
    model = Post

    class Update(SmartUpdateView):
        readonly = ('tags',)

**permission**

Let's you set what permission the user must have in order to view this page.

**template_name**

The name of the template used to render this view.  By default, this is set to ``smartmin/create.html`` but you can override it to whatever you'd like.

Overriding
------------

You can also extend your SmartCreateView to modify behavior at runtime, the most common methods to override are listed below.

**pre_save**

Called after our form has been validated and cleaned and our object created, but before the object has actually been saved.  This can be a good place to add derived attributes to your model.

**post_save**

Called after our object has been saved.  Sometimes used to add permissions.

**get_success_url**

Returns what URL the page should go to after the form has been successfully submitted.



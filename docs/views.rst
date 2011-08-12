Smartmin Views
==================

Smartmin comes with five views defined.  One each for, Create, Read, Update, Delete and List on your custom model objects.  Each of these views can be used individually as you would any Django class based view, or they can be used together in a CRUDL object.

Whenever using a CRUDL object, you are implicitely creating views for each of the CRUDL actions.  For example, if you define a CRUDL for a Post object, as so::

  class PostCRUDL(SmartCRUDL):
    model = Post

You are implicitely creating views for the CRUDL operations.  If you'd rather only include some actions, that is easily done by setting the ``actions`` tuple::

  class PostCRUDL(SmartCRUDL):
    actions = ('create', 'update', 'list')
    model = Post

Now, only the views to create, update and list objects will be created and wired.

You can also choose to override any of the views for a CRUDL, without losing all the URL magic.  The SmartCRUDL object will use any inner class of itself that is named the same as the action::

  class PostCRUDL(SmartCRUDL):
    actions = ('create', 'update', 'list')
    model = Post

    class List(SmartListView):
      fields = ('title', 'body')

When created, the List class will be used instead of the default Smartmin generated list view.  This let's you easily override behavior as you see fit.


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

SmartListView
==================

The SmartListView provides the most bang for the buck, and was largely inspired by Django's own admin list API.  It has the following options:

**fields**

Defines which fields should be displayed in the list, and in what order.  

The order of precedence to get the field value is first the View, by calling ``get_${field_name}``, then the object itself.  This means you can easily define custom formatting of a field for a list view by simply declaring a new method::

  class PostListView(SmartListView):
    model = Post
    fields = ('title', 'body')

    def get_body(self, obj):
      # only display first 50 characters of body
      return obj.body[:50]

Note that if you'd like to have this be set at runtime, you can do so by overriding the ``derive_fields`` method

**link_fields**

Defines which fields should be turned into links to the object itself.  By default, this is just the first item in the field list, but you can change it as you wish, including having more than one field.  By default Smartmin will generate a link to the 'read' view for the object.

You can modify what the link is by overriding ``lookup_field_link``::

  class List(SmartListView):
    model = Country
    link_fields = ('name', 'currency')

    def lookup_field_link(self, context, field, obj):
      # Link our name and currency fields, each going to their own place
      if field == 'currency':
        return reverse('locales.currency_update', args=[obj.currency.id])
      else:
        return reverse('locales.country_update', args=[obj.id])

Note that if you'd like to have this be set at runtime, you can do so by overriding the ``derive_link_fields`` method

**search_fields**

If set, then enables a search box which will search across the passed in fields.  This should be a list or tuple.  The values are used to build up a Q object, so you can specify standard Django manipulations if you'd like::

  class List(SmartListView):
    model = User    
    search_fields = ('username__icontains','first_name__icontains', 'last_name__icontains')

Alternatively, if you want to customize the search even further, you can modify how the query is built by overriding the ``derive_queryset`` method.

**template_name**

The name of the template used to render this view.  By default, this is set to ``smartmin/list.html`` but you can override it to whatever you'd like.

**add_button**

Whether an add button should be automatically added for this list view.  Generally used with CRUDL.


    



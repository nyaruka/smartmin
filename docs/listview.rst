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


    



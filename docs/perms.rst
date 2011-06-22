
Group Creation
================

Smartmin believes in using groups and permissions to manage access to all your site resources.  Managing these can be a bare in Django however as the permission and group ids can change out from under you, making fixtures ill suited.

Smartmin addresses this by letting you define your groups and the permissions for those groups within your ``settings.py``.  Every time you run ``python manage.py syncdb``, smartmin will examine your settings and models and make sure all the permissions in sync.

Defining Permissions
======================

You can define permissions per object or alternatively for all objects.  Here we create the default smartmin 'create', 'read', 'update', 'list', 'delete' permissions on all objects::

  PERMISSIONS = {
    '*': ('create', # can create an object
          'read',   # can read an object, viewing it's details
          'update', # can update an object
          'delete', # can delete an object,
          'list'),  # can view a list of the objects
  }

You can also add specific permissions for particular objects if you'd like by specifying the path to the object and the verb you'd like to use for the permission::

  PERMISSIONS = {
    'fruits.apple': ('pick',)
  }

Smartmin will name this permission automatically in the form: ``fruits.apple_pick``.  Note that this is slightly different than standard Django convention, which usually uses the order of 'verb'->'object', but Smartmin does this on purpose so that URL reverse names and permissions are named identically.

Assigning Permissions for Groups
==================================

It is usually most convenient to assign users to particular groups, and assign permissions per group.  Smartmin makes this easy by allowing you to define the groups that exist in your system, and the permissions granted to them via the settings file.  Here's an example::

  GROUP_PERMISSIONS = {
    "Administrator": ('auth.user_create', 'auth.user_read', 'auth.user_update', 
                      'auth.user_delete', 'auth.user_list'),
    "Fruit Picker": ('fruits.apple_list', 'fruits.apple_pick'),
  }

Again, these groups and permissions will automatically be created and granted when you run ``python manage.py syncdb``

If you want a particular user to have *ALL* permissions on an object, you can do so by using a wildcard format.  For example, to have the Administrator group above be able to perform any action on the user object, you could use: ``auth.user.*``::

  GROUP_PERMISSIONS = {
    "Administrator": ('auth.user.*', ),
    "Fruit Picker": ('fruits.apple_list', 'fruits.apple_pick'),
  }


Permissions on Views
=====================

Smartmin supports gating any view using permissions.  If you are using a CRUDL object, all you need to do is set ``permissions = True``::

  class FruitCRUDL(SmartCRUDL):
    model = Fruit
    permissions = True

But you can also customize permissions on a per view basis by setting the permission on the View itself::

  class FruitListView(SmartListView):
    model = Fruit
    permission = 'fruits.apple_list'

The user will automatically be redirected to a login page if they try to access this view.

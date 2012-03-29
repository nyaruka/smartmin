.. Django Smartmin documentation master file, created by
   sphinx-quickstart on Mon Jun 20 16:37:41 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Introduction
===========================================

Smartmin was born out of the frustration of the Django admin site not being well suited to being exposed to clients.  Smartmin aims to allow you to quickly build scaffolding which you can customize by using Django 1.3's views.

It is very opininated in how it works, if you don't agree, Smartmin may not be for you:

- Permissions are used to gate access to each page, embrace permissions throughout and you'll love this
- CRUDL operations at the object level, that is, Create, Read, Update, Delete and List, permissions and views are based around this
- URL automapping via the the CRUDL objects, this should keep things very very DRY

The full documentation can be found at:
  http://readthedocs.org/docs/smartmin/en/latest/

The official source code repository is:
  http://www.github.com/nyaruka/smartmin/

Built in Rwanda by Nyaruka Ltd:
  http://www.nyaruka.com


Dependencies
===========================================

Smartmin depends on features in Django 1.3, so you'll need to be running at least that version.  It also depends on the most excellent django-guardian package to deal with object level permissions, so you'll need to install that as well.

Installation
===========================================

The easiest and fastest way of downloading smartmin is from the cheeseshop::

    % pip install smartmin

This will take care of installing all the appropriate dependencies as well.

Configuration
===========================================

To get started with smartmin, the following changes to your ``settings.py`` are needed::

  # create the smartmin CRUDL permissions on all objects
  PERMISSIONS = {
    '*': ('create', # can create an object
          'read',   # can read an object, viewing it's details
          'update', # can update an object
          'delete', # can delete an object,
          'list'),  # can view a list of the objects
  }

  # assigns the permissions that each group should have, here creating an Administrator group with 
  # authority to create and change users
  GROUP_PERMISSIONS = {
      "Administrator": ('auth.user.*',)
  }

  # this is required by guardian
  ANONYMOUS_USER_ID = -1

  # set this if you want to use smartmin's user login
  LOGIN_URL = '/users/login'

You'll also need to add smartmin and guardian to your installed apps::

  INSTALLED_APPS = (
    # .. other apps ..

    'guardian',
    'smartmin',
  )

Finally, if you want to use the default smartmin views for managing users and logging in, you'll want to add the smartmin.users app to your ``urls.py``::

  urlpatterns = patterns('',
    # .. other patterns ..
    url(r'^users/', include('smartmin.users.urls')),
  )

You can now sync your database and start the server::

   % python manage.py syncdb
   % python manage.py runserver

And if you want to see a Smartmin view in action, check out smartmin's user management pages for a demo that functionality by pointing your browser to::

    http://localhost:8000/users/user

From here you can create, update and list users on the system, all using standard smartmin views.  The total code to create all this functionality is less than 30 lines of Python.

Versioning:
===========================================

Smartmin will release major versions in step (or rather a bit behind) Django's major releases.  That is the version 1.3.* series are made to work with Django 1.3.  Version 1.4.* is made to work with Django 1.4.*.  Although we try not to rock the boat too much, Smartmin is still actively changing, so we don't guarantee any backwards compatability between major releases.

At the onset of each new Django version we will upgrade Twitter Bootstrap to the current version.  Currently for 1.4, which targets Django 1.4, that means Twitter Bootstrap 2.


Contents:
===========================================

.. toctree::
   :maxdepth: 2

   quickstart
   views
   createview
   readview
   updateview
   deleteview
   listview
   crudl
   templates
   perms
   misc

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


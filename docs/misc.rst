Miscelaneous Utilities
========================

We've included a few bonus features that we find useful when developing django apps.

Django Compressor
===================

Smartmin already comes with django-compressor support.  The default ``base.html`` template will wrap your CSS and JS in ``{% compress %}`` tags in order to optimize your page load times.

If you want to enable this, you'll just need to add ``compressor`` to your ``INSTALLED_APPS`` in ``settings.py``::

  INSTALLED_APPS = (
    # .. other apps ..
    'compressor',
  )

And change the commented out ``{# compress #}`` tags in ``base.html`` to be valid, ie: ``{% compress %}``.


pdb Template Tag
===================

We all love ``pdb.set_trace()`` to help us debug problems, but sometimes you want to do the same thing in a template.  The smartmin template tags include just that::

   {% pdb %}

Will throw you into a pdb session when it hits that tag.  You can examine variables in the session (including the request) and debug your template live.

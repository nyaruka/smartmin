Miscellaneous Utilities
========================

We've included a few bonus features that we find useful when developing django apps.

Collect SQL Command
-------------------

This is a management command to extract SQL operations from your Django migrations and organize them into several master
SQL scripts::

  python manage.py collect_sql

This will extract any SQL statements passed to RunSQL operations and write them to ``current_indexes.sql``,
``current_triggers.sql`` and ``current_functions.sql``.

Migrate Manual Command
----------------------

This is a management command to make it easier to run long-running Django data migrations manually. To make a migration
compatible with this command, include a function called ``apply_manual`` which takes no parameters::

  python manage.py migrate_manual flows 0123

This will manually run the migration in the flows app with the prefix 0123.

Django Compressor
-----------------

Smartmin already comes with django-compressor support.  The default ``base.html`` template will wrap your CSS and JS in
``{% compress %}`` tags in order to optimize your page load times.

If you want to enable this, you'll just need to add ``compressor`` to your ``INSTALLED_APPS`` in ``settings.py``::

  INSTALLED_APPS = (
    # .. other apps ..
    'compressor',
  )

And change the commented out ``{# compress #}`` tags in ``base.html`` to be valid, ie: ``{% compress %}``.


PDB Template Tag
----------------

We all love ``pdb.set_trace()`` to help us debug problems, but sometimes you want to do the same thing in a template.
The smartmin template tags include just that::

   {% pdb %}

Will throw you into a pdb session when it hits that tag.  You can examine variables in the session (including the
request) and debug your template live.

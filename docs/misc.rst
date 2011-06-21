Miscelaneous Utilities
========================

We've included a few bonus features that we find useful when developing django apps.

pdb Template Tag
===================

We all love ``pdb.set_trace()`` to help us debug problems, but sometimes you want to do the same thing in a template.  The smartmin template tags include just that::

   {% pdb %}

Will throw you into a pdb session when it hits that tag.  You can examine variables in the session (including the request) and debug your template live.

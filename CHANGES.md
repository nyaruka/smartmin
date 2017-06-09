1.11.1 (2017-06-09)
====================
 * Fix date widget so that initial values are correctly formatted

1.11 (2017-06-07)
====================
 * Add support for Django 1.11, drop support for Django 1.8
 * Remove django-guardian (no more object-level or anonymous user permissions)
 * Updated datepicker Javascript library https://github.com/nyaruka/smartmin/pull/101
 * Fix bug when form field is bound to empty many-to-many relation https://github.com/nyaruka/smartmin/pull/102

1.10.10 (2017-04-04)
====================
 * Add status_code arg to assertRedirect to allow checking of different redirect types
 * Make jQuery inclusion into block which can be overridden

1.10.8 (2017-03-03)
===================
 * Fix bug on list views when search string is empty https://github.com/nyaruka/smartmin/pull/94

1.10.6 (2017-02-24)
===================
 * Replace usage of auto_now and auto_now_add with overridable defaults https://github.com/nyaruka/smartmin/pull/93

1.10.5 (2017-01-24)
==================
 * JSON views updated to use MIME type application/json
 
1.10.4 (2017-01-23)
==================
 * Add SmartObjectActionView

1.10.2 (2016-12-19)
==================
 * Add task_status field on ImportTask replacing celery result use for task status https://github.com/nyaruka/smartmin/pull/89

1.10.1 (2016-12-14)
==================
 * Added missing migration https://github.com/nyaruka/smartmin/pull/86
 * Fixed using arg for get_form which was removed in Django 1.10 https://github.com/nyaruka/smartmin/pull/88
 
1.10 (2016-12-14)
==================
 * Support for Django 1.10

1.9.3 (2016-11-18)
==================
 * Fixed filename length bug in CSV imports https://github.com/nyaruka/smartmin/pull/85

1.9.2 (2016-10-18)
==================
 * Fixed some Python 3.5 and migration issues https://github.com/nyaruka/smartmin/pull/83

1.9.1 (2016-10-14)
==================
 * Fixed some Python 3 issues https://github.com/nyaruka/smartmin/pull/82
 
1.9.0 (2016-10-11)
==================
 * Support for Django 1.9

1.8.0 (2015-07-10)
==================
 * Support for Django 1.8
 * Releases now published to pypi

1.7.0 (2014-12-01)
==================
 * Support for Django 1.7

1.4.0 (2012-03-29)
=================
 * Support for Django 1.4

0.0.2 (2011-06-21)
==============
 * Added datepicker widget as default for date fields
 * Added imagethumbnail widget as default for images
 * Added sorting functionality
 * Add subfield lookups for all 'field' configurations

0.0.1
==============
 * Initial version

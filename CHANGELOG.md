v5.2.4 (2026-01-08)
-------------------------
 * Bump python versions for CI
 * Switch from Poetry to uv package manager
 * Update django dependency

v5.2.2 (2025-06-13)
-------------------------
 * Make celery/redis dev only dependencies

v5.2.1 (2025-06-10)
-------------------------
 * Merge pull request #205 from nyaruka/dependabot/pip/django-5.1.10
 * Bump django from 5.1.4 to 5.1.10

v5.2.0 (2025-05-13)
-------------------------
 * Update to support django 5.2

v5.1.2 (2025-02-10)
-------------------------
 * Remove CSV import functionality
 * Update pyproject.toml for poetry 2

v5.1.1 (2024-11-25)
-------------------------
 * Smartmin doesn't concern itself with formax

v5.1.0 (2024-08-16)
-------------------------
 * Support Django 5.1

v5.0.10 (2024-07-18)
-------------------------
 * Revert "Update xlrd library"

v5.0.9 (2024-07-17)
-------------------------
 * Update xlrd library

v5.0.8 (2024-07-11)
-------------------------
 * Merge pull request #194 from nyaruka/update-deps
 * Update deps

v5.0.7 (2024-06-26)
-------------------------
 * Change default button name for update views to just Save

v5.0.6 (2024-06-13)
-------------------------
 * Add related names and replace auto_now_add on user app models

v5.0.5 (2024-06-12)
-------------------------
 * Support Python 3.12
 * Update password recovery link validity time to 1 hour

v5.0.4 (2024-06-11)
-------------------------
 * Rework perms again, this time to configure the perms for each app individually

v5.0.3 (2024-06-11)
-------------------------
 * Refactor permissions code

v5.0.2 (2024-05-16)
-------------------------
 * Add SMARTMIN_DEFAULT_MESSAGES setting to allow disabling of automatic messages for create and update views

v5.0.1 (2024-04-17)
-------------------------
 * Merge pull request #185 from nyaruka/dependabot/pip/sqlparse-0.5.0
 * Bump sqlparse from 0.4.4 to 0.5.0
 * Merge pull request #184 from nyaruka/dependabot/pip/pillow-10.3.0
 * Bump pillow from 10.2.0 to 10.3.0
 * Merge pull request #183 from nyaruka/dependabot/pip/black-24.3.0
 * Merge pull request #182 from nyaruka/dependabot/pip/django-5.0.3
 * Bump black from 23.11.0 to 24.3.0
 * Bump django from 5.0 to 5.0.3
 * Merge pull request #180 from nyaruka/dependabot/pip/pillow-10.2.0
 * Bump pillow from 10.1.0 to 10.2.0

v5.0.0 (2023-12-06)
-------------------------
 * Support django 5.0

v4.2.5 (2023-11-03)
-------------------------
 * Merge pull request #178 from nyaruka/update-deps
 * Update deps

v4.2.4 (2023-10-05)
-------------------------
 * Merge pull request #176 from nyaruka/dependabot/pip/pillow-10.0.1
 * Bump pillow from 9.5.0 to 10.0.1

v4.2.3 (2023-08-15)
-------------------------
 * Fix for python 3.11
 * Update CI test versions and dev deps
 * Allow all views to override title using title field

v4.2.2 (2023-02-20)
-------------------------
 * Bump django from 4.1.6 to 4.1.7

v4.2.1 (2023-01-20)
-------------------------
 * Allow Django 4.1 and newer versions of celery and redis

v4.2.0 (2023-01-20)
-------------------------
 * Use latest Django 4.0.* and test against Django 4.1.*

v4.1.0
----------
 * Remove broken and unused middleware classes
 * Bump pillow from 8.4.0 to 9.0.0

v4.0.1
----------
 * Add NOOP migrations created by change in Django 4.0

v4.0.0
----------
 * Use timezone.utc instead of pytz.UTC
 * Update allowed Django versions to < 4.1 and replace removed functions

v3.1.0
----------
 * Update to celery 5.1

v3.0.1
----------
 * Replace the default SmartView.as_json implementation with a NotImplementedError as it can never work

v3.0.0
----------
 * Ad support for Django 3.2 LTS

v2.3.9
----------
 * Add support for Form.Meta.labels and Form.Meta.help_texts

v2.3.8
----------
 * Fix pagination index

v2.3.7
----------
 * Fix thumbnail widget to only use sorl function if we have an image value

v2.3.6
----------
 * Revert redis downgrade
 * Use thumnail image in the image widget when we have the sorl thumbnail installed

v2.3.5
----------
 * Downgrade xlrd dep to 1.2.0

v2.3.4
----------
 * Update deps, downgrading redis requirement

v2.3.3
----------
 * Rework login view so we can reuse it more easily when user isn't determined by form
 * Add data migrations to remove all failed logins
 * Replace FailedLogin user field by username

v2.3.2
----------
 * Merge pull request #143 from nyaruka/forget-password-email-no-user-settings
 * Merge pull request #142 from nyaruka/update-jquery
 * Disable sending emails to address without user in the system
 * Add settings to configure whether we send email when no user is found, default to False
 * Update jquery
 * Bump CI testing to PG 11 and 12

v2.3.1
----------
 * Convert to poetry
 * Tweak collec_sql verbose logging and add test for dropping functions

2.3 (2020-10-27)
================
* Fix collect_sql not tracking overloaded functions
* Drop support for Python 3.5
* Test against Postgres 10 and 11

2.2.4 (2020-09-10)
==================
* Fix collect_sql not catching indexes using UNIQUE

2.2.3 (2020-09-09)
==================
* Don't use a transaction for CSV import tasks

2.1.1 (2019-01-07)
==================
* Fix domain names in forgot password emails
* Test against PostgreSQL 10

2.1.0 (2018-11-27)
==================
* Add support for Django 2.1

2.0.2 (2018-10-01)
==================

* Fix CSV import file_path truncation

2.0.1 (2018-09-12)
==================

* Stop embedding refresh code on pages that don't have View.refresh set

2.0.0 (2018-07-25)
==================

* Add support for Django 2.0, drop support for Django 1.9 and Django 1.10
* Drop support for Python2

1.11.9 (2018-05-3)
===================
 * Create SmartminTestMixin https://github.com/nyaruka/smartmin/pull/116
 * add 'create_anonymous_user' method that will ensure that anonymous user exists

1.11.8 (2018-03-15)
===================
 * Fix Python 3 exception usage https://github.com/nyaruka/smartmin/pull/114

1.11.7 (2018-02-23)
===================
 * Fix Python 3 issue with comparing ints and None https://github.com/nyaruka/smartmin/pull/113

1.11.6 (2017-12-11)
===================
 * Fix collect_sql when objects of different types have same name https://github.com/nyaruka/smartmin/pull/111

1.11.5 (2017-11-15)
====================
 * Add collect_sql and migrate_manual management commands https://github.com/nyaruka/smartmin/pull/108
 
 1.11.4 (2017-11-08)
====================
 * Strip whitespace from usernames on the login form https://github.com/nyaruka/smartmin/pull/106
 * Make sure that we don't strip whitespaces on password fields (default Django behaviour)

1.11.3 (2017-06-28)
====================
 * Paging fix https://github.com/nyaruka/smartmin/pull/105
 * Replace custom class_from_string with Django's import_string
 
1.11.2 (2017-06-15)
====================
 * Support Django 1.10 new middleware style

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

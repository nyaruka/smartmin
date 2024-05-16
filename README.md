Django Smartmin
===============

[![Build Status](https://github.com/nyaruka/smartmin/workflows/CI/badge.svg)](https://github.com/nyaruka/smartmin/actions?query=workflow%3ACI) 
[![codecov](https://codecov.io/gh/nyaruka/smartmin/branch/main/graph/badge.svg)](https://codecov.io/gh/nyaruka/smartmin)
[![PyPI Release](https://img.shields.io/pypi/v/smartmin.svg)](https://pypi.python.org/pypi/smartmin/)

Smartmin was born out of the frustration of the Django admin site not being well suited to being exposed to clients. 
It aims to allow you to quickly build scaffolding which you can customize by using Django views.

It is very opinionated in how it works, if you don't agree, Smartmin may not be for you:

- Permissions are used to gate access to each page, embrace permissions throughout and you'll love this
- CRUDL operations at the object level, that is, Create, Read, Update, Delete and List, permissions and views are based 
  around this
- URL automapping via the the CRUDL objects, this should keep things very very DRY

About Versions
==============

Smartmin tries to stay in lock step with the latest Django versions. With each new major Django release we will release
a new Smartmin major version and we will reserve major changes (possibly breaking backwards compatibility) for such 
releases.

The latest version is the 5.* series which supports the Django 5.0 and 4.2.

About
=====

The full documentation can be found at: http://readthedocs.org/docs/smartmin/en/latest/

The official source code repository is: http://www.github.com/nyaruka/smartmin/

Built in Rwanda by [Nyaruka Ltd](http://www.nyaruka.com).

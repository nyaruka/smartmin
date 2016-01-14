#!/bin/sh

cd ..
python setup.py develop
pip install coverage
pip install django-celery
pip install pysqlite

coverage run manage.py test test_runner.blog.tests --noinput --verbosity=2
coverage report -i


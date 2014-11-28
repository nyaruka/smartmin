#!/bin/sh

cd ..
python setup.py develop
pip install django-nose
pip install coverage
pip install django-celery
pip install pysqlite

python manage.py test test_runner.blog.tests -s --pdb --noinput --with-coverage --cover-package=smartmin --cover-html-dir=../coverage-report --cover-html



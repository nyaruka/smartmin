To upload to PyPi
--------------------

```shell
% pip install pypandoc wheel twine
% brew install pandoc
% rm -R dist/
% python setup.py sdist
% python setup.py bdist_wheel --universal
% twine upload -u nicpottier dist/*
```
from __future__ import unicode_literals

from django.test import TestCase
from .models import ImportTask, generate_file_path


class ImportTest(TestCase):
    def test_csv_import(self):
        pass

    def test_generate_file_path(self):
        self.assertEquals(generate_file_path(ImportTask(), 'allo.csv'), 'csv_imports/allo.csv')
        self.assertEquals(generate_file_path(ImportTask(), 'allo.xlsx'), 'csv_imports/allo.xlsx')
        self.assertEquals(generate_file_path(ImportTask(), 'allo.foo.bar'), 'csv_imports/allo.foo.bar')

        self.assertEquals(generate_file_path(ImportTask(),
                                             'some_import_file_name_really_very_long_to_need_to_truncated_at_'
                                             'the_maximum_lenght_allowed_by_django_file_field.abc.xls.csv'),
                          'csv_imports/some_import_file_name_really_very_long_to_need_to_truncated_.csv')

        self.assertEquals(generate_file_path(ImportTask(),
                                             'some_import_file_name_really_very_long_to_need_to_truncated_at_'
                                             'the_maximum_lenght_allowed_by_django_file_field.abc.xlsx'),
                          'csv_imports/some_import_file_name_really_very_long_to_need_to_truncated.xlsx')

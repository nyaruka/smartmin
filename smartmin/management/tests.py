from unittest.mock import patch, call

from django.core.management import call_command
from django.db.migrations import RunSQL, RunPython
from django.test import TestCase

from .commands.collect_sql import SqlType, SqlObjectOperation


class MockMigration(object):
    def __init__(self, operations):
        self.operations = operations


def mock_run_python(apps, schema_editor):
    pass


class CollectSqlTest(TestCase):

    @patch('smartmin.management.commands.collect_sql.Command.load_migrations')
    @patch('smartmin.management.commands.collect_sql.Command.write_dump')
    def test_command(self, mock_write_dump, mock_load_migrations):
        mock_load_migrations.return_value = [
            MockMigration(operations=[
                RunSQL("CREATE INDEX test_1 ON foo(bar); CREATE INDEX test_2 ON foo(bar);"),
                RunPython(mock_run_python)
            ]),
            MockMigration(operations=[
                RunSQL("DROP INDEX test_2;"),
            ]),
            MockMigration(operations=[
                RunSQL("CREATE TRIGGER test_1 AFTER TRUNCATE ON flows_flowstep EXECUTE PROCEDURE foo();"),
                RunSQL("CREATE INDEX a_test ON foo(bar);"),
                RunPython(mock_run_python)
            ]),
        ]

        call_command('collect_sql', output_dir='sql')

        mock_write_dump.assert_has_calls([
            call('indexes', [
                SqlObjectOperation("CREATE INDEX a_test ON foo(bar);", SqlType.INDEX, "a_test", True),
                SqlObjectOperation("CREATE INDEX test_1 ON foo(bar);", SqlType.INDEX, "test_1", True),
            ], 'sql'),
            call('triggers', [
                SqlObjectOperation("CREATE TRIGGER test_1 AFTER TRUNCATE ON flows_flowstep EXECUTE PROCEDURE foo();",
                                   SqlType.TRIGGER, "test_1", True)
            ], 'sql')
        ])

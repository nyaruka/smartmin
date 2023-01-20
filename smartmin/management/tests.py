from unittest.mock import call, patch

from django.core.management import call_command
from django.db.migrations import RunPython, RunSQL
from django.test import TestCase

from .commands.collect_sql import SqlObjectOperation, SqlType


class MockMigration(object):
    def __init__(self, operations):
        self.operations = operations


def mock_run_python(apps, schema_editor):
    pass


class CollectSqlTest(TestCase):
    @patch("smartmin.management.commands.collect_sql.Command.load_migrations")
    @patch("smartmin.management.commands.collect_sql.Command.write_dump")
    def test_command(self, mock_write_dump, mock_load_migrations):
        mock_load_migrations.return_value = [
            MockMigration(
                operations=[
                    RunSQL(
                        """
CREATE INDEX test_1 ON foo(bar);
CREATE INDEX test_2 ON foo(bar); create unique index test_3 on foo(bar);
"""
                    ),
                    RunPython(mock_run_python),
                ]
            ),
            MockMigration(
                operations=[
                    RunSQL("DROP INDEX test_2;"),
                ]
            ),
            MockMigration(
                operations=[
                    RunSQL("CREATE TRIGGER test_1 AFTER TRUNCATE ON flows_flowstep EXECUTE PROCEDURE foo();"),
                    RunSQL("CREATE INDEX a_test ON foo(bar);"),
                    RunPython(mock_run_python),
                ]
            ),
            MockMigration(
                operations=[
                    RunSQL(
                        "CREATE OR REPLACE FUNCTION a_func(i INTEGER, s TEXT) RETURNS integer AS $$ BEGIN RETURN i + 1; END; $$ LANGUAGE plpgsql;"
                    ),
                    # different function because it has different parameters
                    RunSQL(
                        "CREATE OR REPLACE FUNCTION a_func(s text, integer) RETURNS text AS $$ BEGIN RETURN UPPER(s); END; $$ LANGUAGE plpgsql;"
                    ),
                    # same function because it has same name and parameters
                    RunSQL(
                        "CREATE OR REPLACE FUNCTION A_FUNC(N integer, V text) RETURNS text AS $$ BEGIN RETURN UPPER(V); END; $$ LANGUAGE plpgsql;"
                    ),
                    RunSQL(
                        "CREATE OR REPLACE FUNCTION func2(i INTEGER) RETURNS integer AS $$ BEGIN RETURN i + 1; END; $$ LANGUAGE plpgsql;"
                    ),
                    RunSQL("DROP FUNCTION func2(i INTEGER);"),
                ]
            ),
        ]

        call_command("collect_sql", output_dir="sql")

        mock_write_dump.assert_has_calls(
            [
                call(
                    "indexes",
                    [
                        SqlObjectOperation(
                            "CREATE INDEX a_test ON foo(bar);",
                            sql_type=SqlType.INDEX,
                            obj_name="a_test",
                            is_create=True,
                        ),
                        SqlObjectOperation(
                            "CREATE INDEX test_1 ON foo(bar);",
                            sql_type=SqlType.INDEX,
                            obj_name="test_1",
                            is_create=True,
                        ),
                        SqlObjectOperation(
                            "create unique index test_3 on foo(bar);",
                            sql_type=SqlType.INDEX,
                            obj_name="test_3",
                            is_create=True,
                        ),
                    ],
                    "sql",
                ),
                call(
                    "functions",
                    [
                        SqlObjectOperation(
                            "CREATE OR REPLACE FUNCTION A_FUNC(N integer, V text) RETURNS text AS $$ BEGIN RETURN UPPER(V); END; $$ LANGUAGE plpgsql;",
                            sql_type=SqlType.FUNCTION,
                            obj_name="A_FUNC(integer,text)",
                            is_create=True,
                        ),
                        SqlObjectOperation(
                            "CREATE OR REPLACE FUNCTION a_func(s text, integer) RETURNS text AS $$ BEGIN RETURN UPPER(s); END; $$ LANGUAGE plpgsql;",
                            sql_type=SqlType.FUNCTION,
                            obj_name="a_func(text,integer)",
                            is_create=True,
                        ),
                    ],
                    "sql",
                ),
                call(
                    "triggers",
                    [
                        SqlObjectOperation(
                            "CREATE TRIGGER test_1 AFTER TRUNCATE ON flows_flowstep EXECUTE PROCEDURE foo();",
                            sql_type=SqlType.TRIGGER,
                            obj_name="test_1",
                            is_create=True,
                        ),
                    ],
                    "sql",
                ),
            ]
        )

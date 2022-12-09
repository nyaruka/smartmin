from collections import OrderedDict
from datetime import datetime
from enum import Enum
from textwrap import dedent

import sqlparse
from sqlparse import sql, tokens, tokens as sql_tokens

from django.core.management.base import BaseCommand
from django.db.migrations import RunSQL
from django.db.migrations.executor import MigrationExecutor


class InvalidSQLException(Exception):
    def __init__(self, s):
        super(InvalidSQLException, self).__init__(f"Invalid SQL: {s}")


class SqlType(Enum):
    """
    The different SQL types that we can extract from migrations
    """

    INDEX = 1
    FUNCTION = 2
    TRIGGER = 3


class SqlObjectOperation:
    def __init__(self, statement, sql_type, obj_name, is_create):
        self.statement = statement
        self.sql_type = sql_type
        self.obj_name = obj_name
        self.is_create = is_create

    @classmethod
    def parse(cls, raw):
        # get non-whitespace non-comment tokens
        tokens = [t for t in raw.tokens if not t.is_whitespace and not isinstance(t, sql.Comment)]
        if len(tokens) < 3:
            return None

        # check statement is of form "CREATE|DROP TYPE ..."
        if tokens[0].ttype != sql_tokens.DDL or tokens[1].ttype != sql_tokens.Keyword:
            return None

        if tokens[0].value.upper() in ("CREATE", "CREATE OR REPLACE"):
            is_create = True
        elif tokens[0].value.upper() in ("DROP",):
            is_create = False
        else:
            return None

        try:
            type_token = tokens[1].value.upper()
            if type_token == "UNIQUE":
                type_token = tokens[2].value.upper()

            sql_type = SqlType[type_token]
        except KeyError:
            return None

        if sql_type == SqlType.FUNCTION:
            function = next(filter(lambda t: isinstance(t, sql.Function), tokens), None)
            if not function:
                raise InvalidSQLException(raw.value)

            name = cls._function_name(function)
        else:
            identifier = next(filter(lambda t: isinstance(t, sql.Identifier), tokens), None)
            if not identifier:
                raise InvalidSQLException(raw.value)

            name = identifier.value

        return cls(raw.value.strip(), sql_type, name, is_create)

    @staticmethod
    def _function_name(func: sql.Function) -> str:
        # possible bug in sqlparse library but Function.get_parameters only returns first identifier
        parenthesis = func.tokens[-1]
        types = [str(t) for t in parenthesis.tokens if t.ttype == tokens.Name.Builtin]

        return f"{func.get_name()}({','.join(types)})"

    def __eq__(self, other):
        return (
            self.statement == other.statement
            and self.sql_type == other.sql_type
            and self.obj_name == other.obj_name
            and self.is_create == other.is_create
        )

    def __repr__(self):
        return f"SqlObjectOperation[type={self.sql_type} name='{self.obj_name}' is_create={self.is_create}]"


class Command(BaseCommand):
    help = """Collects SQL statements from migrations to compile lists of indexes, functions and triggers"""

    def add_arguments(self, parser):
        parser.add_argument(
            "--preserve-order",
            action="store_true",
            dest="preserve_order",
            default=False,
            help="Whether to preserve order of operations rather than sorting by object name.",
        )
        parser.add_argument(
            "--output-dir",
            action="store",
            dest="output_dir",
            default="temba/sql",
            help="The output directory for generated SQL files.",
        )

    def handle(self, *args, **options):
        preserve_order = options.get("preserve_order")
        output_dir = options.get("output_dir")

        self.verbosity = options.get("verbosity")

        self.stdout.write("Loading migrations...")

        migrations = self.load_migrations()

        self.stdout.write("Loaded %s migrations" % self.style.SUCCESS(len(migrations)))
        self.stdout.write("Extracting SQL operations...")

        operations = self.extract_operations(migrations)

        self.stdout.write("Extracted %s SQL operations" % self.style.SUCCESS(len(operations)))
        self.stdout.write("Normalizing SQL operations...")

        normalized = self.normalize_operations(operations)

        self.stdout.write("Removed %s redundant operations" % self.style.SUCCESS(len(operations) - len(normalized)))

        self.write_type_dumps(normalized, preserve_order, output_dir)

    def load_migrations(self):  # pragma: no cover
        """
        Loads all migrations in the order they would be applied to a clean database
        """
        executor = MigrationExecutor(connection=None)

        # create the forwards plan Django would follow on an empty database
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes(), clean_start=True)

        if self.verbosity >= 2:
            for migration, _ in plan:
                self.stdout.write(" > %s" % migration)

        return [m[0] for m in plan]

    def extract_operations(self, migrations):
        """
        Extract SQL operations from the given migrations
        """
        operations = []

        for migration in migrations:
            for operation in migration.operations:
                if isinstance(operation, RunSQL):
                    statements = sqlparse.parse(dedent(operation.sql))

                    for statement in statements:
                        operation = SqlObjectOperation.parse(statement)
                        if operation:
                            operations.append(operation)

                            if self.verbosity >= 2:
                                self.stdout.write(" > % -100s (%s)" % (operation, migration))

        return operations

    def normalize_operations(self, operations):
        """
        Removes redundant SQL operations - e.g. a CREATE X followed by a DROP X
        """
        normalized = OrderedDict()

        for operation in operations:
            op_key = (operation.sql_type, operation.obj_name.lower())

            # do we already have an operation for this object?
            if op_key in normalized:
                if self.verbosity >= 2:
                    self.stdout.write(" < %s" % normalized[op_key])

                del normalized[op_key]

            # don't add DROP operations for objects not previously created
            if operation.is_create:
                normalized[op_key] = operation
            elif self.verbosity >= 2:
                self.stdout.write(" < %s" % operation)

        return normalized.values()

    def write_type_dumps(self, operations, preserve_order, output_dir):
        """
        Splits the list of SQL operations by type and dumps these to separate files
        """
        by_type = {SqlType.INDEX: [], SqlType.FUNCTION: [], SqlType.TRIGGER: []}
        for operation in operations:
            by_type[operation.sql_type].append(operation)

        # optionally sort each operation list by the object name
        if not preserve_order:
            for obj_type, ops in by_type.items():
                by_type[obj_type] = sorted(ops, key=lambda o: o.obj_name)

        if by_type[SqlType.INDEX]:
            self.write_dump("indexes", by_type[SqlType.INDEX], output_dir)
        if by_type[SqlType.FUNCTION]:
            self.write_dump("functions", by_type[SqlType.FUNCTION], output_dir)
        if by_type[SqlType.TRIGGER]:
            self.write_dump("triggers", by_type[SqlType.TRIGGER], output_dir)

    def write_dump(self, type_label, operations, output_dir):  # pragma: no cover
        filename = "%s/current_%s.sql" % (output_dir, type_label)

        with open(filename, "w") as f:
            header = "-- Generated by collect_sql on %s UTC\n\n" % datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            f.write(header)

            for operation in operations:
                f.write(operation.statement)
                f.write("\n\n")

        self.stdout.write("Saved %s" % filename)

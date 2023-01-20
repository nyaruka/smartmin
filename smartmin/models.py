import csv
import json
import traceback
import zoneinfo
from datetime import datetime

from xlrd import XL_CELL_DATE, XLRDError, open_workbook, xldate_as_tuple

from django.conf import settings
from django.db import models
from django.utils import timezone


class SmartImportRowError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class SmartModel(models.Model):
    """
    Useful abstract base class that adds the concept of something being active,
    having a user that created or modified the item and creation and modification
    dates.
    """

    is_active = models.BooleanField(
        default=True, help_text="Whether this item is active, use this instead of deleting"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_creations",
        help_text="The user which originally created this item",
    )
    created_on = models.DateTimeField(
        default=timezone.now, editable=False, blank=True, help_text="When this item was originally created"
    )

    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_modifications",
        help_text="The user which last modified this item",
    )
    modified_on = models.DateTimeField(
        default=timezone.now, editable=False, blank=True, help_text="When this item was last modified"
    )

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields", None)

        if (update_fields is None or "modified_on" in update_fields) and not kwargs.pop("preserve_modified_on", False):
            self.modified_on = timezone.now()

        return super(SmartModel, self).save(*args, **kwargs)

    class Meta:
        abstract = True

    @classmethod
    def prepare_fields(cls, field_dict, import_params=None, user=None):
        return field_dict

    @classmethod
    def create_instance(cls, field_dict):
        return cls.objects.create(**field_dict)

    @classmethod
    def validate_import_header(cls, header):
        return

    @classmethod
    def get_import_file_headers(cls, csv_file):
        filename = csv_file
        headers = []
        try:
            workbook = open_workbook(filename.name, "rb")

            for sheet in workbook.sheets():

                # read our header
                header = []
                for col in range(sheet.ncols):
                    header.append(str(sheet.cell(0, col).value))
                headers = [cls.normalize_value(_).lower() for _ in header]

                # only care for the first sheet
                break
        except XLRDError:
            # our alternative codec, by default we are the crazy windows encoding
            ascii_codec = "cp1252"

            # read the entire file, look for mac_roman characters
            reader = open(filename.name, "rb")
            for byte in reader.read():
                # these are latin accented characterse in mac_roman, if we see them then our alternative
                # encoding should be mac_roman
                try:
                    byte_number = ord(byte)
                except TypeError:
                    byte_number = byte

                if byte_number in [0x81, 0x8D, 0x8F, 0x90, 0x9D]:
                    ascii_codec = "mac_roman"
                    break
            reader.close()

            reader = open(filename.name, "rU", encoding="utf-8-sig")

            def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
                csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
                for row in csv_reader:
                    encoded = []
                    for cell in row:
                        try:
                            cell = str(cell)
                        except Exception:
                            cell = str(cell.decode(ascii_codec))

                        encoded.append(cell)

                    yield encoded

            reader = unicode_csv_reader(reader)

            # read in our header
            line_number = 0

            header = next(reader)
            line_number += 1
            while header is not None and len(header[0]) > 1 and header[0][0] == "#":
                header = next(reader)
                line_number += 1

            # do some sanity checking to make sure they uploaded the right kind of file
            if len(header) < 1:
                raise Exception("Invalid header for import file")

            # normalize our header names, removing quotes and spaces
            headers = [cls.normalize_value(_).lower() for _ in header]

        return headers

    @classmethod
    def finalize_import(cls, task, records):
        """
        Provides SmartModels a hook to perform any last updates on imported records outside the import
        database transaction.
        """
        return

    @classmethod
    def import_csv(cls, task, log=None):
        csv_file = task.csv_file
        csv_file.open()

        # this file isn't good enough, lets write it to local disk
        import os
        from uuid import uuid4

        from django.conf import settings

        # make sure our tmp directory is present (throws if already present)
        try:
            os.makedirs(os.path.join(settings.MEDIA_ROOT, "tmp"))
        except Exception:
            pass

        # write our file out
        tmp_file = os.path.join(settings.MEDIA_ROOT, "tmp/%s" % str(uuid4()))

        out_file = open(tmp_file, "wb")
        out_file.write(csv_file.read())
        out_file.close()

        filename = out_file
        user = task.created_by

        import_params = None
        import_results = dict()

        # additional parameters are optional
        if task.import_params:
            try:
                import_params = json.loads(task.import_params)
            except Exception:
                pass

        try:
            records = cls.import_xls(filename, user, import_params, log, import_results)
        except XLRDError:
            records = cls.import_raw_csv(filename, user, import_params, log, import_results)
        finally:
            os.remove(tmp_file)

        task.import_results = json.dumps(import_results)

        return records

    @classmethod
    def normalize_value(cls, val):
        # remove surrounding whitespace
        val = val.strip()

        # if surrounded by double quotes, remove those
        if val and val[0] == '"' and val[-1] == '"':
            val = val[1:-1]

        # if surrounded by single quotes, remove those
        if val and val[0] == "'" and val[-1] == "'":
            val = val[1:-1]

        return val

    @classmethod
    def import_xls(cls, filename, user, import_params, log=None, import_results=None):
        workbook = open_workbook(filename.name, "rb")

        # timezone for date cells can be specified as an import parameter or defaults to UTC
        # use now to determine a relevant timezone
        naive_timezone = (
            zoneinfo.ZoneInfo(import_params["timezone"])
            if import_params and "timezone" in import_params
            else timezone.utc
        )
        tz = timezone.now().astimezone(naive_timezone).tzinfo

        records = []
        num_errors = 0
        error_messages = []

        for sheet in workbook.sheets():
            # read our header
            header = []
            for col in range(sheet.ncols):
                header.append(str(sheet.cell(0, col).value))
            header = [cls.normalize_value(_).lower() for _ in header]

            cls.validate_import_header(header)

            # read our rows
            line_number = 1
            for row in range(sheet.nrows - 1):
                field_values = []
                for col in range(sheet.ncols):
                    cell = sheet.cell(row + 1, col)
                    field_values.append(cls.get_cell_value(workbook, tz, cell))

                field_values = dict(zip(header, field_values))
                field_values["created_by"] = user
                field_values["modified_by"] = user

                try:
                    field_values = cls.prepare_fields(field_values, import_params, user)
                    record = cls.create_instance(field_values)

                    if record:
                        records.append(record)
                    else:
                        num_errors += 1

                except SmartImportRowError as e:
                    error_messages.append(dict(line=line_number + 1, error=str(e)))

                except Exception as e:
                    if log:
                        traceback.print_exc(100, log)
                    raise Exception("Line %d: %s\n\n%s" % (line_number, str(e), field_values))
                line_number += 1
            # only care about the first sheet
            break

        if import_results is not None:
            import_results["records"] = len(records)
            import_results["errors"] = num_errors + len(error_messages)
            import_results["error_messages"] = error_messages

        return records

    @classmethod
    def get_cell_value(cls, workbook, tz, cell):
        if cell.ctype == XL_CELL_DATE:
            date = xldate_as_tuple(cell.value, workbook.datemode)
            return datetime(*date, tzinfo=tz)
        else:
            return cls.normalize_value(str(cell.value))

    @classmethod
    def import_raw_csv(cls, filename, user, import_params, log=None, import_results=None):
        # our alternative codec, by default we are the crazy windows encoding
        ascii_codec = "cp1252"

        # read the entire file, look for mac_roman characters
        reader = open(filename.name, "rb")
        for byte in reader.read():
            # these are latin accented characterse in mac_roman, if we see them then our alternative
            # encoding should be mac_roman
            try:
                byte_number = ord(byte)
            except TypeError:
                byte_number = byte

            if byte_number in [0x81, 0x8D, 0x8F, 0x90, 0x9D]:
                ascii_codec = "mac_roman"
                break
        reader.close()

        reader = open(filename.name, "rU", encoding="utf-8-sig")

        def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
            csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
            for row in csv_reader:
                encoded = []
                for cell in row:
                    try:
                        cell = str(cell)
                    except Exception:
                        cell = str(cell.decode(ascii_codec))

                    encoded.append(cell)

                yield encoded

        reader = unicode_csv_reader(reader)

        # read in our header
        line_number = 0

        header = next(reader)
        line_number += 1
        while header is not None and len(header[0]) > 1 and header[0][0] == "#":
            header = next(reader)
            line_number += 1

        # do some sanity checking to make sure they uploaded the right kind of file
        if len(header) < 1:
            raise Exception("Invalid header for import file")

        # normalize our header names, removing quotes and spaces
        header = [cls.normalize_value(_).lower() for _ in header]

        cls.validate_import_header(header)

        records = []
        num_errors = 0
        error_messages = []

        for row in list(reader):
            # trim all our values
            row = [cls.normalize_value(_) for _ in row]

            line_number += 1

            # make sure there are same number of fields
            if len(row) != len(header):
                raise Exception(
                    "Line %d: The number of fields for this row is incorrect. Expected %d but found %d."
                    % (line_number, len(header), len(row))
                )

            field_values = dict(zip(header, row))
            field_values["created_by"] = user
            field_values["modified_by"] = user
            try:
                field_values = cls.prepare_fields(field_values, import_params, user)
                record = cls.create_instance(field_values)
                if record:
                    records.append(record)
                else:
                    num_errors += 1

            except SmartImportRowError as e:
                error_messages.append(dict(line=line_number, error=str(e)))

            except Exception as e:
                if log:
                    traceback.print_exc(100, log)
                raise Exception("Line %d: %s\n\n%s" % (line_number, str(e), field_values))

        if import_results is not None:
            import_results["records"] = len(records)
            import_results["errors"] = num_errors + len(error_messages)
            import_results["error_messages"] = error_messages

        return records


class ActiveManager(models.Manager):
    """
    A manager that only selects items which are still active.
    """

    def get_queryset(self):
        """
        Where the magic happens, we automatically throw on an extra is_active = True to every filter
        """
        return super(ActiveManager, self).get_queryset().filter(is_active=True)

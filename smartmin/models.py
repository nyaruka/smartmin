import csv
import datetime
import traceback
import simplejson
from django.db import models
from django.contrib.auth.models import User
from pytz import timezone, UTC
from xlrd import open_workbook, xldate_as_tuple, XL_CELL_DATE, XLRDError


class SmartModel(models.Model):
    """
    Useful abstract base class that adds the concept of something being active,
    having a user that created or modified the item and creation and modification
    dates.
    """
    is_active = models.BooleanField(default=True,
                                    help_text="Whether this item is active, use this instead of deleting")

    created_by = models.ForeignKey(User, related_name="%(app_label)s_%(class)s_creations",
                                   help_text="The user which originally created this item")    
    created_on = models.DateTimeField(auto_now_add=True,
                                      help_text="When this item was originally created")

    modified_by = models.ForeignKey(User, related_name="%(app_label)s_%(class)s_modifications",
                                    help_text="The user which last modified this item")
    modified_on = models.DateTimeField(auto_now=True,
                                       help_text="When this item was last modified")

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
            workbook = open_workbook(filename.name, 'rb')

            records = []

            for sheet in workbook.sheets():

                # read our header
                header = []
                for col in range(sheet.ncols):
                    header.append(unicode(sheet.cell(0, col).value))
                headers = [cls.normalize_value(_).lower() for _ in header]

                #only care for the first sheet
                break
        except XLRDError:
            # our alternative codec, by default we are the crazy windows encoding
            ascii_codec = 'cp1252'

            # read the entire file, look for mac_roman characters
            reader = open(filename.name, "rb")
            for byte in reader.read():
                # these are latin accented characterse in mac_roman, if we see them then our alternative
                # encoding should be mac_roman
                if ord(byte) in [0x81, 0x8d, 0x8f, 0x90, 0x9d]:
                    ascii_codec = 'mac_roman'
                    break
            reader.close()
            
            reader = open(filename.name, "rU")

            def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
                csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
                for row in csv_reader:
                    encoded = []
                    for cell in row:
                        try:
                            cell = unicode(cell)
                        except:
                            cell = unicode(cell.decode(ascii_codec))

                        encoded.append(cell)
                        
                yield encoded

            reader = unicode_csv_reader(reader)

            # read in our header
            line_number = 0

            header = reader.next()
            line_number += 1
            while header is not None and len(header[0]) > 1 and header[0][0] == "#":
                header = reader.next()
                line_number += 1

            # do some sanity checking to make sure they uploaded the right kind of file
            if len(header) < 1:
                raise Exception("Invalid header for import file")

            # normalize our header names, removing quotes and spaces
            headers = [cls.normalize_value(_).lower() for _ in header]
            
        return headers


    @classmethod
    def import_csv(cls, task, log=None):
        filename = task.csv_file.file
        user = task.created_by

        import_params = None

        # additional parameters are optional
        if task.import_params:
            try:
                import_params = simplejson.loads(task.import_params)
            except:
                pass

        try:
            records = cls.import_xls(filename, user, import_params, log)
        except XLRDError:
            records = cls.import_raw_csv(filename, user, import_params, log)

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
    def import_xls(cls, filename, user, import_params, log=None):
        workbook = open_workbook(filename.name, 'rb')

        # timezone for date cells can be specified as an import parameter or defaults to UTC
        tz = timezone(import_params['timezone']) if import_params and 'timezone' in import_params else UTC

        records = []

        for sheet in workbook.sheets():
            # read our header
            header = []
            for col in range(sheet.ncols):
                header.append(unicode(sheet.cell(0, col).value))
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
                field_values['created_by'] = user
                field_values['modified_by'] = user

                try:
                    field_values = cls.prepare_fields(field_values, import_params, user)
                    record = cls.create_instance(field_values)
                    if record:
                        records.append(record)
                except Exception as e:
                    if log:
                        traceback.print_exc(100, log)
                    raise Exception("Line %d: %s\n\n%s" % (line_number, str(e), field_values))
                line_number += 1
            # only care about the first sheet
            break

        return records


    @classmethod
    def get_cell_value(cls, workbook, tz, cell):
        if cell.ctype == XL_CELL_DATE:
            date = xldate_as_tuple(cell.value, workbook.datemode)
            return datetime.datetime(*date, tzinfo=tz)
        else:
            return cls.normalize_value(unicode(cell.value))


    @classmethod
    def import_raw_csv(cls, filename, user, import_params, log=None):
        # our alternative codec, by default we are the crazy windows encoding
        ascii_codec = 'cp1252'

        # read the entire file, look for mac_roman characters
        reader = open(filename.name, "rb")
        for byte in reader.read():
            # these are latin accented characterse in mac_roman, if we see them then our alternative
            # encoding should be mac_roman
            if ord(byte) in [0x81, 0x8d, 0x8f, 0x90, 0x9d]:
                ascii_codec = 'mac_roman'
                break
        reader.close()

        reader = open(filename.name, "rU")

        def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
            csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
            for row in csv_reader:
                encoded = []
                for cell in row:
                    try:
                        cell = unicode(cell)
                    except:
                        cell = unicode(cell.decode(ascii_codec))

                    encoded.append(cell)

                yield encoded

        reader = unicode_csv_reader(reader)

        # read in our header
        line_number = 0

        header = reader.next()
        line_number += 1
        while header is not None and len(header[0]) > 1 and header[0][0] == "#":
            header = reader.next()
            line_number += 1

        # do some sanity checking to make sure they uploaded the right kind of file
        if len(header) < 1:
            raise Exception("Invalid header for import file")

        # normalize our header names, removing quotes and spaces
        header = [cls.normalize_value(_).lower() for _ in header]

        cls.validate_import_header(header)

        records = []
        for row in reader:
            # trim all our values
            row = [cls.normalize_value(_) for _ in row]

            line_number += 1

            # make sure there are same number of fields
            if len(row) != len(header):
                raise Exception("Line %d: The number of fields for this row is incorrect. Expected %d but found %d." % (line_number, len(header), len(row)))

            field_values = dict(zip(header, row))
            field_values['created_by'] = user
            field_values['modified_by'] = user
            try:
                field_values = cls.prepare_fields(field_values, import_params, user)
                record = cls.create_instance(field_values)
                if record:
                    records.append(record)
            except Exception as e:
                if log:
                    traceback.print_exc(100, log)
                raise Exception("Line %d: %s\n\n%s" % (line_number, str(e), field_values))
        return records

class ActiveManager(models.Manager):
    """
    A manager that only selects items which are still active.
    """
    def get_query_set(self):
        """
        Where the magic happens, we automatically throw on an extra is_active = True to every filter
        """
        return super(ActiveManager, self).get_query_set().filter(is_active=True)

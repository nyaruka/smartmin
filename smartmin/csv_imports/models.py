from django.db import models, transaction
from smartmin import class_from_string
from django.utils import timezone

from smartmin.models import SmartModel

class ImportTask(SmartModel):
    csv_file = models.FileField(upload_to="csv_imports", verbose_name="Import file", help_text="A comma delimited file of records to import")
    model_class = models.CharField(max_length=255, help_text="The model we are importing for")
    import_params = models.TextField(blank=True, null=True, help_text="JSON blob of form parameters on task creation")
    import_log = models.TextField()
    task_id = models.CharField(null=True, max_length=64)

    def start(self):
        from .tasks import csv_import
        self.log("Queued import at %s" % timezone.now())
        result = csv_import.delay(self.pk)
        self.task_id = result.task_id
        self.save()

    def done(self):
        from .tasks import csv_import
        if self.task_id:
            result = csv_import.AsyncResult(self.task_id)
            return result.ready()

    def status(self):
        from .tasks import csv_import
        status = "PENDING"
        if self.task_id:
            result = csv_import.AsyncResult(self.task_id)
            status = result.state
        return status

    def log(self, message):
        self.import_log += "%s\n" % message
        self.modified_on = timezone.now()
        self.save()

    def get_import_file_headers(self):
        filename = self.csv_file.file
        from xlrd import open_workbook, XLRDError
            
        headers =[]
        try:
            workbook = open_workbook(filename.name, 'rb')

            records = []

            for sheet in workbook.sheets():

                # read our header
                header = []
                for col in range(sheet.ncols):
                    header.append(unicode(sheet.cell(0, col).value))
                headers = [ImportTask.normalize_value(_).lower() for _ in header]

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

    def __unicode__(self):
        return "%s Import" % class_from_string(self.model_class)._meta.verbose_name.title()

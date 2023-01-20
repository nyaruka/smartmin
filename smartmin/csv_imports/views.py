from django.utils.module_loading import import_string

from smartmin.csv_imports.models import ImportTask
from smartmin.views import SmartCRUDL, SmartListView, SmartReadView


class ImportTaskCRUDL(SmartCRUDL):
    model = ImportTask
    actions = ("read", "list")

    class Read(SmartReadView):
        def derive_refresh(self):
            if self.object.status() in ["PENDING", "RUNNING", "STARTED"]:
                return 2000
            else:
                return 0

    class List(SmartListView):
        fields = ("status", "type", "csv_file", "created_on", "created_by")
        link_fields = ("csv_file",)

        def get_type(self, obj):
            return import_string(obj.model_class)._meta.verbose_name_plural.title()

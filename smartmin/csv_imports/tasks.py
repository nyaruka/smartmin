from __future__ import unicode_literals

import django

from celery.task import task
from distutils.version import StrictVersion
from django.utils import timezone
from time import sleep
from smartmin import class_from_string
from .models import ImportTask

# python2 and python3 support
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


@task(track_started=True)
def csv_import(task_id):  # pragma: no cover
    from django.db import transaction

    # there is a possible race condition between this task starting and the db object being created,
    # so we have a bit of loop here to fetch the task
    tries = 0
    import_task = None
    while not import_task:
        try:
            import_task = ImportTask.objects.get(pk=task_id)
        except Exception as e:
            # this object just doesn't exist yet, sleep a bit then try again
            tries +=1
            if tries >= 75:
                raise e
            else:
                sleep(1)

    log = StringIO()

    if StrictVersion(django.get_version()) < StrictVersion('1.6'):

        transaction.enter_transaction_management()
        transaction.managed()

        try:
            import_task.task_id = csv_import.request.id
            import_task.log("Started import at %s" % timezone.now())
            import_task.log("--------------------------------")
            import_task.save()

            transaction.commit()

            model = class_from_string(import_task.model_class)
            records = model.import_csv(import_task, log)
            import_task.save()

            import_task.log(log.getvalue())
            import_task.log("Import finished at %s" % timezone.now())
            import_task.log("%d record(s) added." % len(records))

            transaction.commit()

        except Exception as e:
            transaction.rollback()

            import traceback
            traceback.print_exc(e)

            import_task.log("\nError: %s\n" % e)
            import_task.log(log.getvalue())
            transaction.commit()

            raise e

        finally:
            transaction.leave_transaction_management()

    else:

        import_task.task_id = csv_import.request.id
        import_task.log("Started import at %s" % timezone.now())
        import_task.log("--------------------------------")
        import_task.save()

        try:
            with transaction.atomic():
                model = class_from_string(import_task.model_class)
                records = model.import_csv(import_task, log)
                import_task.save()

                import_task.log(log.getvalue())
                import_task.log("Import finished at %s" % timezone.now())
                import_task.log("%d record(s) added." % len(records))

        except Exception as e:
            import traceback
            traceback.print_exc(e)

            import_task.log("\nError: %s\n" % e)
            import_task.log(log.getvalue())

            raise e

    return import_task

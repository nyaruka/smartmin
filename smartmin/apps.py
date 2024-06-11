from django.apps import AppConfig
from django.db.models.signals import post_migrate


class SmartminConfig(AppConfig):
    name = "smartmin"

    def ready(self):
        from .perms import sync_permissions

        post_migrate.connect(sync_permissions)

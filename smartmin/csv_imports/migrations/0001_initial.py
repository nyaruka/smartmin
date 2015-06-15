# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ImportTask',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_active', models.BooleanField(default=True, help_text=b'Whether this item is active, use this instead of deleting')),
                ('created_on', models.DateTimeField(help_text=b'When this item was originally created', auto_now_add=True)),
                ('modified_on', models.DateTimeField(help_text=b'When this item was last modified', auto_now=True)),
                ('csv_file', models.FileField(help_text=b'A comma delimited file of records to import', upload_to=b'csv_imports', verbose_name=b'Import file')),
                ('model_class', models.CharField(help_text=b'The model we are importing for', max_length=255)),
                ('import_params', models.TextField(help_text=b'JSON blob of form parameters on task creation', null=True, blank=True)),
                ('import_log', models.TextField()),
                ('import_results', models.TextField(help_text=b'JSON blob of result values on task completion', null=True, blank=True)),
                ('task_id', models.CharField(max_length=64, null=True)),
                ('created_by', models.ForeignKey(related_name='csv_imports_importtask_creations', to=settings.AUTH_USER_MODEL, help_text=b'The user which originally created this item')),
                ('modified_by', models.ForeignKey(related_name='csv_imports_importtask_modifications', to=settings.AUTH_USER_MODEL, help_text=b'The user which last modified this item')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]

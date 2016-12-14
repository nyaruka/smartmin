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
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this item is active, use this instead of deleting')),
                ('created_on', models.DateTimeField(help_text='When this item was originally created', auto_now_add=True)),
                ('modified_on', models.DateTimeField(help_text='When this item was last modified', auto_now=True)),
                ('name', models.SlugField(help_text='The name of this category', unique=True, max_length=64)),
                ('created_by', models.ForeignKey(related_name='blog_category_creations', to=settings.AUTH_USER_MODEL, help_text='The user which originally created this item')),
                ('modified_by', models.ForeignKey(related_name='blog_category_modifications', to=settings.AUTH_USER_MODEL, help_text='The user which last modified this item')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this item is active, use this instead of deleting')),
                ('created_on', models.DateTimeField(help_text='When this item was originally created', auto_now_add=True)),
                ('modified_on', models.DateTimeField(help_text='When this item was last modified', auto_now=True)),
                ('title', models.CharField(help_text='The title of this blog post, keep it relevant', max_length=128)),
                ('body', models.TextField(help_text='The body of the post, go crazy')),
                ('order', models.IntegerField(help_text='The order for this post, posts with smaller orders come first')),
                ('tags', models.CharField(help_text='Any tags for this post', max_length=128)),
                ('created_by', models.ForeignKey(related_name='blog_post_creations', to=settings.AUTH_USER_MODEL, help_text='The user which originally created this item')),
                ('modified_by', models.ForeignKey(related_name='blog_post_modifications', to=settings.AUTH_USER_MODEL, help_text='The user which last modified this item')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]

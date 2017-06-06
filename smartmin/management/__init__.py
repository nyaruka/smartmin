from __future__ import unicode_literals

import six
import sys

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission, Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_migrate
from smartmin.perms import assign_perm, remove_perm

permissions_app_name = None


def get_permissions_app_name():
    """
    Gets the app after which smartmin permissions should be installed. This can be specified by PERMISSIONS_APP in the
    Django settings or defaults to the last app with models
    """
    global permissions_app_name

    if not permissions_app_name:
        permissions_app_name = getattr(settings, 'PERMISSIONS_APP', None)

        if not permissions_app_name:
            app_names_with_models = [a.name for a in apps.get_app_configs() if a.models_module is not None]
            if app_names_with_models:
                permissions_app_name = app_names_with_models[-1]

    return permissions_app_name


def is_permissions_app(app_config):
    """
    Returns whether this is the app after which permissions should be installed.
    """
    return app_config.name == get_permissions_app_name()


def check_role_permissions(role, permissions, current_permissions):
    """
    Checks the the passed in role (can be user, group or AnonymousUser)  has all the passed
    in permissions, granting them if necessary.
    """
    role_permissions = []

    # get all the current permissions, we'll remove these as we verify they should still be granted
    for permission in permissions:
        splits = permission.split(".")
        if len(splits) != 2 and len(splits) != 3:
            sys.stderr.write("  invalid permission %s, ignoring\n" % permission)
            continue

        app = splits[0]
        codenames = []

        if len(splits) == 2:
            codenames.append(splits[1])
        else:
            (object, action) = splits[1:]

            # if this is a wildcard, then query our database for all the permissions that exist on this object
            if action == '*':
                for perm in Permission.objects.filter(codename__startswith="%s_" % object, content_type__app_label=app):
                    codenames.append(perm.codename)
            # otherwise, this is an error, continue
            else:
                sys.stderr.write("  invalid permission %s, ignoring\n" % permission)
                continue

        if len(codenames) == 0:
            continue

        for codename in codenames:
            # the full codename for this permission
            full_codename = "%s.%s" % (app, codename)

            # this marks all the permissions which should remain
            role_permissions.append(full_codename)

            try:
                assign_perm(full_codename, role)
            except ObjectDoesNotExist:
                pass
                # sys.stderr.write("  unknown permission %s, ignoring\n" % permission)

    # remove any that are extra
    for permission in current_permissions:
        if isinstance(permission, six.text_type):
            key = permission
        else:
            key = "%s.%s" % (permission.content_type.app_label, permission.codename)

        if key not in role_permissions:
            remove_perm(key, role)


def check_all_group_permissions(sender, **kwargs):
    """
    Checks that all the permissions specified in our settings.py are set for our groups.
    """
    if not is_permissions_app(sender):
        return

    config = getattr(settings, 'GROUP_PERMISSIONS', dict())

    # for each of our items
    for name, permissions in config.items():
        # get or create the group
        (group, created) = Group.objects.get_or_create(name=name)
        if created:
            pass

        check_role_permissions(group, permissions, group.permissions.all())


def add_permission(content_type, permission):
    """
    Adds the passed in permission to that content type.  Note that the permission passed
    in should be a single word, or verb.  The proper 'codename' will be generated from that.
    """
    # build our permission slug
    codename = "%s_%s" % (content_type.model, permission)

    # sys.stderr.write("Checking %s permission for %s\n" % (permission, content_type.name))

    # does it already exist
    if not Permission.objects.filter(content_type=content_type, codename=codename):
        Permission.objects.create(content_type=content_type,
                                  codename=codename,
                                  name="Can %s %s" % (permission, content_type.name))
        # sys.stderr.write("Added %s permission for %s\n" % (permission, content_type.name))


def check_all_permissions(sender, **kwargs):
    """
    This syncdb checks our PERMISSIONS setting in settings.py and makes sure all those permissions
    actually exit.
    """
    if not is_permissions_app(sender):
        return

    config = getattr(settings, 'PERMISSIONS', dict())

    # for each of our items
    for natural_key, permissions in config.items():
        # if the natural key '*' then that means add to all objects
        if natural_key == '*':
            # for each of our content types
            for content_type in ContentType.objects.all():
                for permission in permissions:
                    add_permission(content_type, permission)

        # otherwise, this is on a specific content type, add for each of those
        else:
            app, model = natural_key.split('.')
            try:
                content_type = ContentType.objects.get_by_natural_key(app, model)
            except ContentType.DoesNotExist:
                continue

            # add each permission
            for permission in permissions:
                add_permission(content_type, permission)


post_migrate.connect(check_all_permissions)
post_migrate.connect(check_all_group_permissions)

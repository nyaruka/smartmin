from django.db.models.signals import post_syncdb
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission, Group
from django.conf import settings
import sys

def check_group_permissions(group, permissions):
    """
    Checks the the passed in group has all the passed in permissions, granting them
    if necessary.
    """
    group_permissions = []
    
    # get all the current permissions, we'll remove these as we verify they should still be granted
    for permission in permissions:
        splits = permission.split(".")
        if len(splits) != 2 and len(splits) != 3:
#            sys.stderr.write("  invalid permission %s, ignoring\n" % permission)
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
#                sys.stderr.write("  invalid permission %s, ignoring\n" % permission)
                continue                

        if len(codenames) == 0:
            continue                            

        for codename in codenames:
            # this marks all the permissions which should remain
            group_permissions.append("%s.%s" % (app, codename))
            
            if not group.permissions.filter(codename=codename, content_type__app_label=app):
                try:
                    group.permissions.add(Permission.objects.get(codename=codename, content_type__app_label=app))
#                    sys.stderr.write(" ++ added %s to %s group\n" % (codename, group.name))
                except Permission.DoesNotExist:
                    pass
#                    sys.stderr.write("  unknown permission %s, ignoring\n" % permission)                

    # remove any that are extra
    for permission in group.permissions.all():
        key = "%s.%s"  % (permission.content_type.app_label, permission.codename)
        if not key in group_permissions:
            group.permissions.remove(permission)
#            sys.stderr.write(" -- removed %s from %s group\n" % (key, group.name))            

def check_all_group_permissions(sender, **kwargs):
    """
    Checks that all the permissions specified in our settings.py are set for our groups.
    """
    config = getattr(settings, 'GROUP_PERMISSIONS', dict())

    # for each of our items
    for name, permissions in config.items():
        # get or create the group
        (group, created) = Group.objects.get_or_create(name=name)
        if created:
            pass
#            sys.stderr.write("Added %s group\n" % name)
        check_group_permissions(group, permissions)


HANDLED_MODELS = set()

def add_permission(content_type, permission):
    """
    Adds the passed in permission to that content type.  Note that the permission passed
    in should be a single word, or verb.  The proper 'codename' will be generated from that.
    """
    # bail if we already handled this model
    key = "%s:%s" % (content_type.model, permission)
    if key in HANDLED_MODELS:
        return
    
    # build our permission slug
    codename = "%s_%s" % (content_type.model, permission)

    # does it already exist
    if not Permission.objects.filter(content_type=content_type, codename=codename):
        Permission.objects.create(content_type=content_type,
                                  codename=codename,
                                  name="Can %s %s" % (permission, content_type.name))
#        sys.stderr.write("Added %s permission for %s\n" % (permission, content_type.name))

    # add this to our cache of handled
    HANDLED_MODELS.add(key)

def check_all_permissions(sender, **kwargs):
    """
    This syncdb checks our PERMISSIONS setting in settings.py and makes sure all those permissions
    actually exit.
    """
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

post_syncdb.connect(check_all_permissions)
post_syncdb.connect(check_all_group_permissions)

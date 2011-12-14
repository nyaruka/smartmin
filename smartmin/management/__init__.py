from django.db.models.signals import post_syncdb
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission, Group, User
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from guardian.shortcuts import assign, remove_perm
from guardian.utils import get_anonymous_user
from guardian.management import create_anonymous_user
import sys

def is_last_model(kwargs):
    """
    Returns whether this is the last post_syncdb called in the application.
    """
    return (kwargs['app'].__name__ == settings.INSTALLED_APPS[-1] + ".models") or (kwargs['app'].__name__ == settings.INSTALLED_APPS[-2] + ".models")

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
                assign(full_codename, role)
            except ObjectDoesNotExist:
                sys.stderr.write("  unknown permission %s, ignoring\n" % permission)                

    # remove any that are extra
    for permission in current_permissions:
        if isinstance(permission, unicode):
            key = permission
        else:
            key = "%s.%s"  % (permission.content_type.app_label, permission.codename)

        if not key in role_permissions:
            remove_perm(key, role)

def check_all_group_permissions(sender, **kwargs):
    """
    Checks that all the permissions specified in our settings.py are set for our groups.
    """
    if not is_last_model(kwargs):
        return

    config = getattr(settings, 'GROUP_PERMISSIONS', dict())

    # for each of our items
    for name, permissions in config.items():
        # get or create the group
        (group, created) = Group.objects.get_or_create(name=name)
        if created:
            pass
#            sys.stderr.write("Added %s group\n" % name)

        check_role_permissions(group, permissions, group.permissions.all())

def get_or_create_anonymous_user():
    try:
        anon_user = get_anonymous_user()
    except:
        create_anonymous_user(None)
        anon_user = get_anonymous_user()

    return anon_user

def check_all_anon_permissions(sender, **kwargs):
    """
    Checks that all our anonymous permissions have been granted
    """
    if not is_last_model(kwargs):
        return

    permissions = getattr(settings, 'ANONYMOUS_PERMISSIONS', [])
    anon_user = get_or_create_anonymous_user()

    check_role_permissions(anon_user, permissions, anon_user.get_all_permissions())

def add_permission(content_type, permission):
    """
    Adds the passed in permission to that content type.  Note that the permission passed
    in should be a single word, or verb.  The proper 'codename' will be generated from that.
    """
    # bail if we already handled this model
    key = "%s:%s" % (content_type.model, permission)
    
    # build our permission slug
    codename = "%s_%s" % (content_type.model, permission)

    # does it already exist
    if not Permission.objects.filter(content_type=content_type, codename=codename):
        Permission.objects.create(content_type=content_type,
                                  codename=codename,
                                  name="Can %s %s" % (permission, content_type.name))
#        sys.stderr.write("Added %s permission for %s\n" % (permission, content_type.name))

def check_all_permissions(sender, **kwargs):
    """
    This syncdb checks our PERMISSIONS setting in settings.py and makes sure all those permissions
    actually exit.
    """
    if not is_last_model(kwargs):
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

post_syncdb.connect(check_all_permissions)
post_syncdb.connect(check_all_group_permissions)
post_syncdb.connect(check_all_anon_permissions)

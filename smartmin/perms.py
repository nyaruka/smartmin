import re

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.management import create_contenttypes
from django.contrib.contenttypes.models import ContentType

perm_desc_regex = re.compile(r"(?P<app>\w+)\.(?P<contenttype>[a-z0-9]+)((_(?P<perm>\w+))|(\.(?P<wild>\*)))")


def update_group_permissions(app, group, permissions: list):
    """
    Checks the the passed in role (can be user, group or AnonymousUser)  has all the passed
    in permissions, granting them if necessary.
    """

    new_permissions = []

    for perm_desc in permissions:
        app_label, content_type, perm = _parse_perm_desc(perm_desc)

        # ignore if this permission is for a type not in this app
        if app_label != app.label:
            continue

        if perm == "*":
            codenames = Permission.objects.filter(
                content_type__app_label=app_label, codename__startswith=f"{content_type}_"
            ).values_list("codename", flat=True)
        else:
            codenames = [f"{content_type}_{perm}"]

        perms = []
        for codename in codenames:
            try:
                perms.append(Permission.objects.get(content_type__app_label=app_label, codename=codename))
            except Permission.DoesNotExist:
                raise ValueError(f"Cannot grant permission {app_label}.{codename} as it does not exist.")

            new_permissions.append((app_label, codename))

        group.permissions.add(*perms)

    # remove any that are extra
    for perm in group.permissions.filter(content_type__app_label=app.label):
        if (perm.content_type.app_label, perm.codename) not in new_permissions:
            group.permissions.remove(perm)


def sync_permissions(sender, **kwargs):
    """
    1. Ensures all permissions for this app described by the PERMISSIONS setting exist in the database.
    2. Ensures all permissions for this app granted by the GROUP_PERMISSIONS setting are granted.
    """

    # the content types app also listens for post_migrate signals but since order isn't guaranteed, we need to
    # manually invoke what it does for this app to be sure that the content types are created
    create_contenttypes(sender)

    # for each of our items
    for natural_key, permissions in getattr(settings, "PERMISSIONS", {}).items():
        # if wild, we add these permissions to all content types defined by this app
        if natural_key == "*":
            for content_type in ContentType.objects.filter(app_label=sender.label):
                for permission in permissions:
                    _ensure_permission_exists(content_type, permission)

        # otherwise check if this type belongs to this app and if so add the permissions to that type only
        else:
            app_label, model = natural_key.split(".")
            if app_label == sender.label:
                try:
                    content_type = ContentType.objects.get_by_natural_key(app_label, model)
                except ContentType.DoesNotExist:
                    raise ValueError(f"No such content type: {app_label}.{model}")

                # add each permission
                for permission in permissions:
                    _ensure_permission_exists(content_type, permission)

    # for each of our items
    for name, permissions in getattr(settings, "GROUP_PERMISSIONS", {}).items():
        # get or create the group
        group, created = Group.objects.get_or_create(name=name)

        update_group_permissions(sender, group, permissions)


def _parse_perm_desc(desc: str) -> tuple:
    """
    Parses a permission descriptor into its app_label, model and permission parts, e.g.
        app.model.*      => app, model, *
        app.model_perm   => app, model, perm
    """

    match = perm_desc_regex.match(desc)
    if not match:
        raise ValueError(f"Invalid permission descriptor: {desc}")

    return match.group("app"), match.group("contenttype"), match.group("perm") or match.group("wild")


def _ensure_permission_exists(content_type, permission: str):
    """
    Adds the passed in permission to that content type.  Note that the permission passed
    in should be a single word, or verb.  The proper 'codename' will be generated from that.
    """

    codename = f"{content_type.model}_{permission}"  # build our permission slug

    Permission.objects.get_or_create(
        content_type=content_type, codename=codename, defaults={"name": f"Can {permission} {content_type.name}"}
    )

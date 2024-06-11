import re

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

permissions_app_name = None
perm_desc_regex = re.compile(r"(?P<app>\w+)\.(?P<codename>\w+)(?P<wild>\.\*)?")


def get_permissions_app_name():
    """
    Gets the app after which smartmin permissions should be installed. This can be specified by PERMISSIONS_APP in the
    Django settings or defaults to the last app with models
    """
    global permissions_app_name

    if not permissions_app_name:
        permissions_app_name = getattr(settings, "PERMISSIONS_APP", None)

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


def update_group_permissions(group, permissions: list):
    """
    Checks the the passed in role (can be user, group or AnonymousUser)  has all the passed
    in permissions, granting them if necessary.
    """

    new_permissions = []

    for perm_desc in permissions:
        app_label, codename, wild = _parse_perm_desc(perm_desc)

        if wild:
            codenames = Permission.objects.filter(
                content_type__app_label=app_label, codename__startswith=f"{codename}_"
            ).values_list("codename", flat=True)
        else:
            codenames = [codename]

        perms = []
        for codename in codenames:
            try:
                perms.append(Permission.objects.get(content_type__app_label=app_label, codename=codename))
            except Permission.DoesNotExist:
                raise ValueError(f"Cannot grant permission {app_label}.{codename} as it does not exist.")

            new_permissions.append((app_label, codename))

        group.permissions.add(*perms)

    # remove any that are extra
    for perm in group.permissions.select_related("content_type").all():
        if (perm.content_type.app_label, perm.codename) not in new_permissions:
            group.permissions.remove(perm)


def sync_permissions(sender, **kwargs):
    """
    1. Ensures all permissions decribed by the PERMISSIONS setting exist in the database.
    2. Ensures all permissions granted by the GROUP_PERMISSIONS setting are granted to the appropriate groups.
    """

    if not is_permissions_app(sender):
        return

    # for each of our items
    for natural_key, permissions in getattr(settings, "PERMISSIONS", {}).items():
        # if the natural key '*' then that means add to all objects
        if natural_key == "*":
            # for each of our content types
            for content_type in ContentType.objects.all():
                for permission in permissions:
                    _ensure_permission_exists(content_type, permission)

        # otherwise, this is on a specific content type, add for each of those
        else:
            app, model = natural_key.split(".")
            try:
                content_type = ContentType.objects.get_by_natural_key(app, model)
            except ContentType.DoesNotExist:
                continue

            # add each permission
            for permission in permissions:
                _ensure_permission_exists(content_type, permission)

    # for each of our items
    for name, permissions in getattr(settings, "GROUP_PERMISSIONS", {}).items():
        # get or create the group
        (group, created) = Group.objects.get_or_create(name=name)
        if created:
            pass

        update_group_permissions(group, permissions)


def _parse_perm_desc(desc: str) -> tuple:
    """
    Parses a permission descriptor into its app_label, model and permission parts, e.g.
        app.model.*      => app, model, True
        app.model_perm   => app, model_perm, False
    """

    match = perm_desc_regex.match(desc)
    if not match:
        raise ValueError(f"Invalid permission descriptor: {desc}")

    return match.group("app"), match.group("codename"), bool(match.group("wild"))


def _ensure_permission_exists(content_type: str, permission: str):
    """
    Adds the passed in permission to that content type.  Note that the permission passed
    in should be a single word, or verb.  The proper 'codename' will be generated from that.
    """

    codename = f"{content_type.model}_{permission}"  # build our permission slug

    Permission.objects.get_or_create(
        content_type=content_type, codename=codename, defaults={"name": f"Can {permission} {content_type.name}"}
    )

from __future__ import unicode_literals

from django.contrib.auth.models import Permission


def assign_perm(perm, group):
    """
    Assigns a permission to a group
    """
    if not isinstance(perm, Permission):
        try:
            app_label, codename = perm.split('.', 1)
        except ValueError:
            raise ValueError("For global permissions, first argument must be in"
                             " format: 'app_label.codename' (is %r)" % perm)
        perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)

    group.permissions.add(perm)
    return perm


def remove_perm(perm, group):
    """
    Removes a permission from a group
    """
    if not isinstance(perm, Permission):
        try:
            app_label, codename = perm.split('.', 1)
        except ValueError:
            raise ValueError("For global permissions, first argument must be in"
                             " format: 'app_label.codename' (is %r)" % perm)
        perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)

    group.permissions.remove(perm)
    return

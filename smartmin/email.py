from __future__ import unicode_literals

from django.conf import settings
from django.utils.module_loading import import_string


def link_components(request, user=None):
    protocol = 'https' if request.is_secure() else 'http'
    hostname = getattr(settings, 'HOSTNAME', request.get_host())

    return {"protocol": protocol, "hostname": hostname}


def build_email_context(request=None, user=None):
    context = {'user': user}

    processors = []
    collect = []
    collect.extend(getattr(settings, "EMAIL_CONTEXT_PROCESSORS",
                           ('smartmin.email.link_components',)))
    for path in collect:
        func = import_string(path)
        processors.append(func)

    for processor in processors:
        context.update(processor(request, user))

    return context

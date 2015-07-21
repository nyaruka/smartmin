from django.conf import settings
from django.template import Context

from django.utils.module_loading import import_string


def build_email_context(request=None, user=None):
    context = Context({'user': user})

    processors = []
    collect = []
    collect.extend(getattr(settings, "EMAIL_CONTEXT_PROCESSORS",
                           ('smartmin.users.context_processors.link_components',)))
    for path in collect:
        func = import_string(path)
        processors.append(func)

    for processor in processors:
        context.update(processor(request))

    return context

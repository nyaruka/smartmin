from __future__ import unicode_literals
from django.conf import settings


def links_components(request):
    protocol = 'https' if request.is_secure() else 'http'
    hostname = getattr(settings, 'HOSTNAME', request.get_host())

    return {"protocol": protocol, "hostname": hostname}





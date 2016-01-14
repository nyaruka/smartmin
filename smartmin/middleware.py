from __future__ import unicode_literals

import sys, os

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from django.utils import timezone
from six.moves import StringIO


class AjaxRedirect(object):
    def process_response(self, request, response):
        if request.is_ajax():
            if type(response) == HttpResponseRedirect:
                # This is our own AJAX friend redirect to allow
                # the calling Javascript the opportunity to deal
                # with redirect responses in its own way
                response = HttpResponse(response["Location"])
                response.status_code = 302
        return response


class ProfileMiddleware():
    def __init__(self):
        pass

    def process_view(self, request, view, *args, **kwargs):
        import hotshot, hotshot.stats

        for item in request.META['QUERY_STRING'].split('&'):
            if item.split('=')[0] == 'profile': # profile in query string
                # catch the output, must happen before stats object is created
                # see https://bugs.launchpad.net/webpy/+bug/133080 for the details
                std_old, std_new = sys.stdout, StringIO.StringIO()
                sys.stdout = std_new

                # now let's do some profiling
                tmpfile = '/tmp/%s' % request.COOKIES['sessionid']
                prof = hotshot.Profile(tmpfile)

                # make a call to the actual view function with the given arguments
                response = prof.runcall(view, request, *args[0], **args[1])
                prof.close()

                # and then statistical reporting
                stats = hotshot.stats.load(tmpfile)
                stats.strip_dirs()
                stats.sort_stats('time')

                # do the output
                stats.print_stats(1.0)

                # restore default output
                sys.stdout = std_old

                # delete file
                os.remove(tmpfile)

                return HttpResponse('<pre>%s</pre>' % std_new.getvalue())

        return None


class TimezoneMiddleware(object):
    def process_request(self, request):
        user_tz = getattr(settings, 'USER_TIME_ZONE', None)

        if user_tz:
            timezone.activate(user_tz)

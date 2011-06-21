__author__ = 'eric'

from django.http import HttpResponseRedirect, HttpResponse

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

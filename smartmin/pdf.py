import os
from io import StringIO

import ho.pisa as pisa

from django.conf import settings
from django.http import HttpResponse
from django.utils.html import escape


class PDFMixin(object):
    """
    Mixin that will change a class based view to render as PDF

    Dependencies:
     - reportlab
     - html5lib
     - pisa
    """

    def render_to_response(self, context, **response_kwargs):

        response = super(PDFMixin, self).render_to_response(context, **response_kwargs)

        # do the actual rendering
        response.render()

        # and get the content
        result = StringIO.StringIO()

        # now render with pisa as PDF
        pdf = pisa.pisaDocument(
            StringIO.StringIO(response.rendered_content.encode("ISO-8859-1")), result, link_callback=fetch_resource
        )
        if not pdf.err:
            return HttpResponse(result.getvalue(), mimetype="application/pdf")
        return HttpResponse("We had some errors<pre>%s</pre>" % escape(response.content))


def fetch_resource(uri, rel):
    path = os.path.join(settings.STATICFILES_DIRS[0], uri.replace(settings.STATIC_URL, ""))
    return path

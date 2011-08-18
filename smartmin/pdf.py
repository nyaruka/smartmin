import ho.pisa as pisa
import StringIO
from django.http import HttpResponse

# Mixin that will change a class based view to render as PDF
#
# Dependencies:
#    - reportlab
#    - html5lib
#    - pisa
#
class PDFMixin(object):

    def render_to_response(self, context, **response_kwargs):
        response = super(PDFMixin, self).render_to_response(context, **response_kwargs)
        
        # do the actual rendering
        response.render()

        # and get the content
        result = StringIO.StringIO()
            
        # now render with pisa as PDF
        pdf = pisa.pisaDocument(StringIO.StringIO(response.rendered_content.encode("ISO-8859-1")), result)
        if not pdf.err:
            return HttpResponse(result.getvalue(), mimetype='application/pdf')
        return HttpResponse('We had some errors<pre>%s</pre>' % escape(html))

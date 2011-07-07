from django.forms import fields
from django.forms import widgets
from django.utils.safestring import mark_safe
from django.utils.html import escape, conditional_escape
import datetime

class VisibleHiddenWidget(widgets.Widget):

    def render(self, name, value, attrs=None):
        """
        Returns this Widget rendered as HTML, as a Unicode string.

        The 'value' given is not guaranteed to be valid input, so subclass
        implementations should program defensively.
        """
        html = ''
        html += '%s' % value
        html += '<input type="hidden" name="%s" value="%s">' % (escape(name), escape(value))
        return mark_safe(html)


class DatePickerWidget(widgets.Widget):

    def __init__(self, *args, **kwargs):
        super(DatePickerWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        """
        Renders this widget as HTML.
        """
        html = ''
        if not value:
            value = datetime.datetime.now().date()

        str_value = "%s %d, %d" % (value.strftime("%B"), value.day, value.year)
        html += '<input type="text" class="datepicker" name="%s" value="%s" readonly="readonly">' % (escape(name), escape(str_value))
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        val = data.get(name)

        # try parsing it
        try:
            parsed = datetime.datetime.strptime(val, "%B %d, %Y")
            return parsed.date()
        except:
            # invalid format?  say so
            return None

    class Media:
       js = ('js/datepicker.js',)
       css = { 'all': ('css/datepicker.css',) }

class ImageThumbnailWidget(widgets.ClearableFileInput): 

    def __init__(self, thumb_width=75, thumb_height=75): 
        self.width = thumb_width 
        self.height = thumb_height 
        super(ImageThumbnailWidget, self).__init__({}) 

    def render(self, name, value, attrs=None): 
        thumb_html = '' 
        if value and hasattr(value, "url"): 
            thumb_html = '<img src="%s" width="%s" width="%s"style="float:left;padding-right:10px;" />' % (value.url, self.width, self.height) 
        return mark_safe("%s%s" % (thumb_html,
                                   super(ImageThumbnailWidget, self).render(name, value, attrs)))        


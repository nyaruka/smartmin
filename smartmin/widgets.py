from __future__ import unicode_literals

from datetime import datetime
from django.forms import widgets
from django.utils.html import escape
from django.utils.safestring import mark_safe


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
        str_value = ""
        if value:
            str_value = "%s %d, %d" % (value.strftime("%B"), value.day, value.year)

        html += '<input type="text" class="datepicker" data-provide="datepicker" name="%s" value="%s" data-date-format="MM d, yyyy" data-date-autoclose="true">' % (escape(name), escape(str_value))
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        val = data.get(name)
        
        # try parsing it
        try:
            parsed = datetime.strptime(val, "%B %d, %Y")
            return parsed.date()
        except Exception:
            # invalid format?  say so
            return None

    class Media:
       js = ('js/datepicker.js',)
       css = {'all': ('css/datepicker.css',)}


class ImageThumbnailWidget(widgets.ClearableFileInput): 

    def __init__(self, thumb_width=75, thumb_height=75): 
        self.width = thumb_width 
        self.height = thumb_height 
        super(ImageThumbnailWidget, self).__init__({}) 

    def render(self, name, value, attrs=None):
        thumb_html = '<table><tr>'
        if value and hasattr(value, "url"): 
            thumb_html += '<td><img src="%s" width="%s" width="%s" /></td>' % (value.url, self.width, self.height) 

        thumb_html += '<td><input type="checkbox" name="%s-clear" /> Clear' % name
        thumb_html += '<input type="file" name="%s" /></td>' % name
        thumb_html += '</tr></table>'

        return mark_safe(unicode('<div class="image-picker">%s</div>' % thumb_html))

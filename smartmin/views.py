from django.db import models

from django.utils.encoding import force_unicode
from django.views.generic.edit import FormMixin, ModelFormMixin, UpdateView, CreateView, ProcessFormView, FormView
from django.views.generic.base import TemplateView, View
from django.views.generic import DetailView, ListView
import django.forms.models as model_forms
from guardian.utils import get_anonymous_user
from django.utils.http import urlquote
from django.db.models import Q
from django.db import IntegrityError
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect, HttpResponse
from guardian.shortcuts import get_objects_for_user, assign
from django.core.exceptions import ImproperlyConfigured
from django import forms
from django.utils import simplejson
from django.conf.urls.defaults import patterns, url
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.models import User

import string
import widgets

def smart_url(url, id=None):
    """
    URLs that start with @ are reversed, using the passed in arguments.

    Otherwise a straight % substitution is applied.
    """
    if url.find("@") >= 0:
        (args, value) = url.split('@')

        if args:
            return reverse(value, args=[id])
        else:
            return reverse(value)
    else:
        if id is None:
            return url
        else:
            return url % id

class SmartView(object):
    fields = None
    exclude = None
    field_config = {}
    title = None
    refresh = 0
    template_name = None

    # set by our CRUDL
    url_name = None

    def __init__(self, *args):
        """
        There are a few variables we want to mantain in the instance, not the
        class.
        """
        self.extra_context = {}
        return super(SmartView, self).__init__(*args)

    def derive_title(self):
        """
        Returns the title used on this page.
        """
        return self.title

    @classmethod
    def derive_url_pattern(cls, path, action):
        """
        Returns the URL pattern for this view.
        """
        return r'^%s/%s/$' % (path, action)

    def has_permission(self, request, *args, **kwargs):
        """
        Figures out if the current user has permissions for this view.
        """
        self.kwargs = kwargs
        self.args = args
        self.request = request

        if not getattr(self, 'permission', None):
            return True
        else:
            # first check our anonymous permissions
            real_anon = get_anonymous_user()
            has_perm = real_anon.has_perm(self.permission)            

            # if not, then check our real permissions
            if not has_perm:
                has_perm = request.user.has_perm(self.permission)

            # if not, perhaps we have it per object
            if not has_perm:
                has_perm = self.has_object_permission('get_object')

            # if still no luck, check if we have permissions on the parent object
            if not has_perm:
                has_perm = self.has_object_permission('get_parent_object')

            return has_perm

    def has_object_permission(self, getter_name):

        """
        Checks for object level permission for an arbitrary getter
        """
        obj = None
        obj_getter = getattr(self, getter_name, None)

        # get object requires pk
        if getter_name == "get_object" and 'pk' not in self.kwargs:
            return False

        if obj_getter:
            obj = obj_getter()
            if obj:
                return self.request.user.has_perm(getattr(self, 'permission', None), obj)

    def dispatch(self, request, *args, **kwargs):
        """
        Overloaded to check permissions if appropriate
        """
        def wrapper(request, *args, **kwargs):
            if not self.has_permission(request, *args, **kwargs):
                path = urlquote(request.get_full_path())
                login_url = kwargs.pop('login_url', settings.LOGIN_URL)
                redirect_field_name = kwargs.pop('redirect_field_name', REDIRECT_FIELD_NAME)
                return HttpResponseRedirect("%s?%s=%s" % (login_url, redirect_field_name, path))
            else:
                response = self.pre_process(request, *args, **kwargs)
                if not response:
                    return super(SmartView, self).dispatch(request, *args, **kwargs)
                else:
                    return response

        return wrapper(request, *args, **kwargs)

    def pre_process(self, request, *args, **kwargs):
        """
        Gives the view an opportunity to intercept this response and return a different
        response instead.  This can be used to check some precondition for example and to
        redirect the user somewhere else if they are not met.

        Views which wish to use this should return a Response object.
        """
        return None

    def lookup_obj_attribute(self, obj, field):
        """
        Looks for a field's value from the passed in obj.  Note that this will strip
        leading attributes to deal with subelements if possible
        """
        curr_field = field
        rest = None

        if field.find('.') >= 0:
            curr_field = field.split('.')[0]
            rest = '.'.join(field.split('.')[1:])

        # next up is the object itself
        obj_field = getattr(obj, curr_field, None)

        # if it is callable, do so
        if obj_field and getattr(obj_field, '__call__', None):
            obj_field = obj_field()

        if obj_field and rest:
            return self.lookup_obj_attribute(obj_field, rest)
        else:
            return obj_field

    def lookup_field_value(self, context, obj, field):
        """
        Looks up the field value for the passed in object and field name.

        Note that this method is actually called from a template, but this provides a hook
        for subclasses to modify behavior if they wish to do so.

        This may be used for example to change the display value of a variable depending on
        other variables within our context.
        """
        # if this isn't a subfield, check the view to see if it has a get_ method
        if field.find('.') == -1:
            # view supercedes all, does it have a 'get_' method for this obj
            view_method = getattr(self, 'get_%s' % field, None)
            if view_method:
                return view_method(obj)

        return self.lookup_obj_attribute(obj, field)

    def lookup_field_label(self, context, field, default=None):
        """
        Figures out what the field label should be for the passed in field name.

        Our heuristic is as follows:
            1) we check to see if our field_config has a label specified
            2) if not, then we derive a field value from the field name
        """
        # if this is a subfield, strip off everything but the last field name
        if field.find('.') >= 0:
            return self.lookup_field_label(context, field.split('.')[-1], default)
        
        label = None

        # is there a label specified for this field
        if field in self.field_config and 'label' in self.field_config[field]:
            label = self.field_config[field]['label']

        # if we were given a default, use that
        elif default:
            label = default

        # check our model
        else:
            for model_field in self.model._meta.fields:
                if model_field.name == field:
                    return model_field.verbose_name.title()

        # otherwise, derive it from our field name
        if label is None:
            label = self.derive_field_label(field)

        return label

    def lookup_field_help(self, field, default=None):
        """
        Looks up the help text for the passed in field.
        """
        help = None

        # is there a label specified for this field
        if field in self.field_config and 'help' in self.field_config[field]:
            help = self.field_config[field]['help']

        # if we were given a default, use that
        elif default:
            help = default

        # try to see if there is a description on our model
        else:
            for model_field in self.model._meta.fields:
                if model_field.name == field:
                    help = model_field.help_text
                    break

        return help

    def lookup_field_class(self, field, obj=None, default=None):
        """
        Looks up any additional class we should include when rendering this field
        """
        css = ""

        # is there a class specified for this field
        if field in self.field_config and 'class' in self.field_config[field]:
            css = self.field_config[field]['class']

        # if we were given a default, use that
        elif default:
            css = default

        return css

    def derive_field_label(self, field, obj=None):
        """
        Derives a field label for the passed in field name.
        """
        # replace _'s with ' '
        label = field.replace('_', ' ').title()
        return label

    def derive_field_config(self):
        """
        Derives the field config for this instance.  By default we just use
        self.field_config
        """
        return self.field_config

    def get_template_names(self):
        """
        Returns the name of the template to use to render this request.

        Smartmin provides default templates as fallbacks, so appends it's own templates names to the end
        of whatever list is built by the generic views.

        Subclasses can override this by setting a 'template_name' variable on the class.
        """
        templates = []
        if getattr(self, 'template_name', None):
            templates.append(self.template_name)

        if getattr(self, 'default_template', None):
            templates.append(self.default_template)
        else:
            templates = super(SmartView, self).get_template_names()
            
        return templates

    def derive_fields(self):
        """
        Default implementation
        """
        fields = []
        if self.fields:
            fields.append(self.fields)

        return fields

    def derive_exclude(self):
        """
        Returns which fields we should exclude
        """
        exclude = []
        if self.exclude:
            exclude += self.exclude

        return exclude

    def derive_refresh(self):
        """
        Returns how many milliseconds before we should refresh
        """
        return self.refresh

    def get_context_data(self, **kwargs):
        """
        We supplement the normal context data by adding our fields and labels.
        """
        context = super(SmartView, self).get_context_data(**kwargs)

        # derive our field config
        self.field_config = self.derive_field_config()

        # add our fields
        self.fields = self.derive_fields()

        # set our blocks
        context['blocks'] = dict()

        # stuff it all in our context
        context['fields'] = self.fields
        context['view'] = self
        context['field_config'] = self.field_config

        context['title'] = self.derive_title()

        # and any extra context the user specified
        context.update(self.extra_context)

        # by default, our base is 'base.html', but we might be pjax
        base_template = "base.html"
        if 'pjax' in self.request.REQUEST or 'pjax' in self.request.POST:
            base_template = "smartmin/pjax.html"
        context['base_template'] = base_template

        # set our refresh if we have one
        refresh = self.derive_refresh()
        if refresh:
            context['refresh'] = refresh

        return context

    def as_json(self, context):
        """
        Responsible for turning our context into an dict that can then be serialized into an
        JSON response.
        """
        return context

    def render_to_response(self, context, **response_kwargs):
        """
        Overloaded to deal with _format arguments.
        """
        # should we actually render in json?
        if '_format' in self.request.REQUEST and self.request.REQUEST['_format'] == 'json':
          json = self.as_json(context)
          return HttpResponse(simplejson.dumps(json), mimetype='application/javascript')

        # otherwise, return normally
        else:
            return super(SmartView, self).render_to_response(context)

class SmartReadView(SmartView, DetailView):
    default_template = 'smartmin/read.html'
    edit_button = False

    field_config = { 'modified_blurb': dict(label="Modified"),
                     'created_blurb': dict(label="Created") }

    def derive_title(self):
        """
        By default we just return the string representation of our object
        """
        return str(self.object)

    @classmethod
    def derive_url_pattern(cls, path, action):
        """
        Returns the URL pattern for this view.
        """
        return r'^%s/%s/(?P<pk>\d+)/$' % (path, action)

    def derive_fields(self):
        """
        Derives our fields.  We first default to using our 'fields' variable if available,
        otherwise we figure it out from our object.
        """
        if self.fields:
            return list(self.fields)

        else:
            fields = []
            for field in self.object._meta.fields:
                fields.append(field.name)
            return fields

    def get_modified_blurb(self, obj):
        return "%s by %s" % (obj.modified_on.strftime("%B %d, %Y at %I:%M %p"), obj.modified_by)

    def get_created_blurb(self, obj):
        return "%s by %s" % (obj.created_on.strftime("%B %d, %Y at %I:%M %p"), obj.created_by)

class SmartDeleteView(SmartView, DetailView, ProcessFormView):
    default_template = 'smartmin/delete_confirm.html'
    name_field = 'name'
    cancel_url = None
    redirect_url = None

    @classmethod
    def derive_url_pattern(cls, path, action):
        """
        Returns the URL pattern for this view.
        """
        return r'^%s/%s/(?P<pk>\d+)/$' % (path, action)

    def get_cancel_url(self):
        if not self.cancel_url:
            raise ImproperlyConfigured("DeleteView must define a cancel_url")

        return smart_url(self.cancel_url)

    def pre_delete(self, obj):
        pass

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.pre_delete(self.object)
        redirect_url = self.get_redirect_url()
        self.object.delete()

        return HttpResponseRedirect(redirect_url)

    def get_redirect_url(self, **kwargs):
        if not self.redirect_url:
            raise ImproperlyConfigured("DeleteView must define a redirect_url")        

        return smart_url(self.redirect_url)

    def get_context_data(self, **kwargs):
        """ Add in the field to use for the name field """
        context = super(SmartDeleteView, self).get_context_data(**kwargs)
        context['name_field'] = self.name_field
        context['cancel_url'] = self.get_cancel_url()
        return context

class SmartListView(SmartView, ListView):
    default_template = 'smartmin/list.html'

    link_url = None
    link_fields = None
    add_button = False
    search_fields = None
    paginate_by = 25
    pjax = None
    field_config = { 'is_active': dict(label=''), }
    default_order = None

    list_permission = None

    @classmethod
    def derive_url_pattern(cls, path, action):
        if action == 'list':
            return r'^%s/$' % (path)
        else:
            return r'^%s/%s/$' % (path, action)

    def derive_title(self):
        """
        Derives our title from our list
        """
        title = super(SmartListView, self).derive_title()

        if not title:
            return force_unicode(self.model._meta.verbose_name_plural).title()
        else:
            return title

    def derive_link_fields(self, context):
        """
        Used to derive which fields should be linked.  This should return a set() containing
        the names of those fields which should be linkable.
        """
        if not self.link_fields is None:
            return self.link_fields

        else:
            link_fields = set()
            if self.fields:
                for field in self.fields:
                    if field != 'is_active':
                        link_fields.add(field)
                        break

        return link_fields

    def lookup_field_link(self, context, field, obj):
        """
        By default we just return /view/{{ id }}/ for the current object.
        """
        return smart_url(self.link_url, str(obj.id))

    def lookup_field_orderable(self, field):
        """
        Returns whether the passed in field is sortable or not, by default all 'raw' fields, that
        is fields that are part of the model are sortable.
        """
        try:
            self.model._meta.get_field_by_name(field)
            return True
        except:
            # that field doesn't exist, so not sortable
            return False

    def get_context_data(self, **kwargs):
        """
        Add in what fields are linkable
        """
        context = super(SmartListView, self).get_context_data(**kwargs)

        # our linkable fields
        self.link_fields = self.derive_link_fields(context)

        # stuff it all in our context
        context['link_fields'] = self.link_fields

        # build up our current parameter string, EXCLUSIVE of our page.  These
        # are used to build pagination URLs
        url_params = "?"
        for key,value in self.request.REQUEST.items():
            if key != 'page' and key != 'pjax' and key[0] != '_':
                url_params += "%s=%s&" % (key, value)
        context['url_params'] = url_params
        context['pjax'] = self.pjax

        # our search term if any
        if 'search' in self.request.REQUEST:
            context['search'] = self.request.REQUEST['search']

        # our ordering field if any
        order = self.derive_ordering()
        if order:
            if order[0] == '-':
                context['order'] = order[1:]
                context['order_asc'] = False
            else:
                context['order'] = order
                context['order_asc'] = True

        return context

    def derive_queryset(self, **kwargs):
        """
        Derives our queryset.
        """
        # get our parent queryset
        queryset = super(SmartListView, self).get_queryset(**kwargs)

        # apply any filtering
        if self.search_fields and 'search' in self.request.REQUEST:
            terms = self.request.REQUEST['search'].split()

            query = Q(pk__gt=0)
            for term in terms:
                term_query = Q(pk__lt=0)
                for field in self.search_fields:
                    term_query |= Q(**{ field: term })
                query &= term_query

            queryset = queryset.filter(query)

        # return our queryset
        return queryset

    def get_queryset(self, **kwargs):
        """
        Gets our queryset.  This takes care of filtering if there are any
        fields to filter by.
        """

        queryset = self.derive_queryset(**kwargs)

        # if our list should be filtered by a permission as well, do so
        if self.list_permission:
            # only filter if this user doesn't have a global permission
            if not self.request.user.has_perm(self.list_permission):
                user = self.request.user
                # guardian only behaves with model users
                if settings.ANONYMOUS_USER_ID and user.is_anonymous():
                    user = User.objects.get(pk=settings.ANONYMOUS_USER_ID)
                queryset = queryset.filter(id__in=get_objects_for_user(user, self.list_permission))

        return self.order_queryset(queryset)

    def derive_ordering(self):
        """
        Returns what field should be used for ordering (using a prepended '-' to indicate descending sort).

        If the default order of the queryset should be used, returns None
        """
        if '_order' in self.request.REQUEST:
            return self.request.REQUEST['_order']
        elif self.default_order:
            return self.default_order
        else:
            return None

    def order_queryset(self, queryset):
        """
        Orders the passed in queryset, returning a new queryset in response.  By default uses the _order query
        parameter.
        """
        order = self.derive_ordering()
        if order:
            # if our order is a single string, convert to a simple list
            if isinstance(order, (str, unicode)):
                order = (order,)

            queryset = queryset.order_by(*order)

        return queryset

    def derive_fields(self):
        """
        Derives our fields.
        """
        if self.fields:
            return self.fields

        else:
            fields = []
            for field in self.object_list.model._meta.fields:
                if field.name != 'id':
                    fields.append(field.name)
            return fields


    def get_is_active(self, obj):
        """
        Default implementation of get_is_active which returns a simple div so as to
        render a green dot for active items and nothing for inactive ones.

        Users of SmartModel will get this rendering for free.
        """
        if obj.is_active:
            return '<div class="active_icon"></div>'
        else:
            return ''

class SmartCsvView(SmartListView):

    def derive_filename(self):
        filename = getattr(self, 'filename', None)
        if not filename:
            filename = "%s.csv" % self.model._meta.verbose_name.lower()
        return filename

    def render_to_response(self, context, **response_kwargs):
        import csv

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s' % self.derive_filename()

        writer = csv.writer(response)
        
        fields = self.derive_fields()

        # build up our header row
        header = []
        for field in fields:
            header.append(self.lookup_field_label(dict(), field))
        writer.writerow(header)

        # then our actual values
        for obj in self.object_list:
            row = []
            for field in fields:
                row.append(self.lookup_field_value(dict(), obj, field))
        writer.writerow(row)

        return response
    
class SmartFormMixin(object):
    readonly = ()
    field_config = { 'modified_blurb': dict(label="Modified"),
                     'created_blurb': dict(label="Created")    }
    success_message = None
    submit_button_name = "Submit"

    def derive_title(self):
        """
        Derives our title from our object
        """
        if not self.title:
            return "Form"
        else:
            return self.title

    def derive_success_message(self):
        """
        Returns a message to display when this form is successfully saved
        """
        self.success_message
    
    def get_form(self, form_class):
        """
        Returns an instance of the form to be used in this view.
        """
        self.form = super(SmartFormMixin, self).get_form(form_class)

        fields = list(self.derive_fields())

        # we specified our own form class, which means we need to apply any field filtering
        # ourselves.. this is ugly but the only way to make exclude and fields work the same
        # despite specifying your own form class
        if self.form_class:
            # only exclude?  then remove those items there
            exclude = self.derive_exclude()
            exclude += self.derive_readonly()

            # remove any excluded fields
            for field in exclude:
                if field in self.form.fields:
                    del self.form.fields[field]
            
            if fields:
                # filter out our form fields
                for name, field in self.form.fields.items():
                    if not name in fields:
                        del self.form.fields[name]


        # stuff in our referer as the default location for where to return
        location = forms.CharField(widget=forms.widgets.HiddenInput(), required=False)

        if ('HTTP_REFERER' in self.request.META):
            location.initial = self.request.META['HTTP_REFERER']

        # add the location to our form fields
        self.form.fields['loc'] = location

        if fields:
            fields.append('loc')

        # provides a hook to programmatically customize fields before rendering
        for (name, field) in self.form.fields.items():
            field = self.customize_form_field(name, field)
            self.form.fields[name] = field

        return self.form

    def customize_form_field(self, name, field):
        """
        Allows views to customize their form fields.  By default, Smartmin replaces the plain textbox
        date input with it's own DatePicker implementation.
        """
        if isinstance(field, forms.fields.DateField) and isinstance(field.widget, forms.widgets.DateInput):
            field.widget = widgets.DatePickerWidget()

        if isinstance(field, forms.fields.ImageField) and isinstance(field.widget, forms.widgets.ClearableFileInput):
            field.widget = widgets.ImageThumbnailWidget()
        
        return field

    def lookup_field_label(self, context, field, default=None):
        """
        Figures out what the field label should be for the passed in field name.

        We overload this so as to use our form to see if there is label set there.  If so
        then we'll pass that as the default instead of having our parent derive
        the field from the name.
        """
        default = None

        for form_field in self.form:
            if form_field.name == field:
                default = form_field.label
                break

        return super(SmartFormMixin, self).lookup_field_label(context, field, default=default)

    def lookup_field_help(self, field, default=None):
        """
        Looks up the help text for the passed in field.

        This is overloaded so that we can check whether our form has help text set
        explicitely.  If so, we will pass this as the default to our parent function.
        """
        default = None

        for form_field in self.form:
            if form_field.name == field:
                default = form_field.help_text
                break

        return super(SmartFormMixin, self).lookup_field_help(field, default=default)

    def derive_readonly(self):
        """
        Figures out what fields should be readonly.  We iterate our field_config to find all
        that have a readonly of true
        """
        readonly = list(self.readonly)
        for key, value in self.field_config.items():
            if 'readonly' in value and value['readonly']:
                readonly.append(key)

        return readonly

    def derive_fields(self):
        """
        Derives our fields.
        """
        fields = []
        if self.fields:
            fields = list(self.fields)

        else:
            form = self.form
            fields = []
            for field in form:
                fields.append(field.name)

            # this is slightly confusing but we add in readonly fields here because they will still
            # need to be displayed
            readonly = self.derive_readonly()
            if readonly:
                fields += readonly

        # remove any excluded fields
        for exclude in self.derive_exclude():
            if exclude in fields:
                fields.remove(exclude)

        return fields

    def get_form_class(self):
        """
        Returns the form class to use in this view
        """
        form_class = None
        
        if self.form_class:
            form_class = self.form_class

        else:
            if self.model is not None:
                # If a model has been explicitly provided, use it
                model = self.model
            elif hasattr(self, 'object') and self.object is not None:
                # If this view is operating on a single object, use
                # the class of that object
                model = self.object.__class__
            else:
                # Try to get a queryset and extract the model class
                # from that
                model = self.get_queryset().model

            # run time parameters when building our form
            factory_kwargs = self.get_factory_kwargs()
            form_class = model_forms.modelform_factory(model, **factory_kwargs)

        return form_class

    def get_factory_kwargs(self):
        """
        Let's us specify any extra parameters we might want to call for our form factory.
        
        These can include: 'form', 'fields', 'exclude' or 'formfield_callback'
        """
        params = dict()

        exclude = self.derive_exclude()
        exclude += self.derive_readonly()

        if self.fields:
            fields = list(self.fields)
            for ex in exclude:
                if ex in fields:
                    fields.remove(ex)
            
            params['fields'] = fields

        if exclude:
            params['exclude'] = exclude

        return params

    def get_success_url(self):
        """
        By default we use the referer that was stuffed in our
        form when it was created
        """
        if self.success_url:
            return smart_url(self.success_url, self.object.pk)
        
        elif 'loc' in self.form.cleaned_data:
            return self.form.cleaned_data['loc']
        
        raise ImproperlyConfigured("No redirect location found, override get_success_url to not use redirect urls")


    def derive_initial(self):
        """
        Returns what initial dict should be passed to our form. By default this is empty.
        """
        return dict()

    def get_form_kwargs(self):
        """
        We override this, using only those fields specified if they are specified.

        Otherwise we include all fields in a standard ModelForm.
        """
        kwargs = super(SmartFormMixin, self).get_form_kwargs()
        kwargs['initial'] = self.derive_initial()
        return kwargs

    def derive_submit_button_name(self):
        """
        Returns the name for our button
        """
        return self.submit_button_name

    def get_context_data(self, **kwargs):
        context = super(SmartFormMixin, self).get_context_data(**kwargs)
        context['submit_button_name'] = self.derive_submit_button_name()
        return context

class SmartFormView(SmartFormMixin, SmartView, FormView):
    default_template = 'smartmin/form.html'

    def form_valid(self, form):
        # plug in our success message
        messages.success(self.request, self.derive_success_message())
        return super(SmartFormView, self).form_valid(form)

class SmartModelFormView(SmartFormMixin, SmartView, ModelFormMixin):
    grant_permissions = None
    javascript_submit = None

    field_config = { 'modified_blurb': dict(label="Modified"),
                     'created_blurb': dict(label="Created") }    

    def derive_title(self):
        """
        Derives our title from our object
        """
        if not self.title:
            return "Edit %s" % force_unicode(self.model._meta.verbose_name).title()
        else:
            return self.title
    
    def pre_save(self, obj):
        """
        Called before an object is saved away
        """
        return obj

    def save(self, obj):
        """
        Actually does the saving of this object, this is when the object is committed
        """
        self.object.save()
        self.save_m2m()

    def form_valid(self, form):
        self.object = form.save(commit=False)

        try:
            self.object = self.pre_save(self.object)
            self.save(self.object)
            self.object = self.post_save(self.object)
        
            messages.success(self.request, self.derive_success_message())
            return HttpResponseRedirect(self.get_success_url())

        except IntegrityError as e:
            message = str(e).capitalize()
            errors = self.form._errors.setdefault(forms.forms.NON_FIELD_ERRORS, forms.util.ErrorList())
            errors.append(message)
            return self.render_to_response(self.get_context_data(form=form))

    def save_m2m(self):
        """
        By default saves the form's m2m, can be overridden if a more complicated m2m model exists
        """
        self.form.save_m2m()

    def post_save(self, obj):
        """
        Called after an object is successfully saved
        """
        # if we have permissions to grant, do so
        if self.grant_permissions:
            for permission in self.grant_permissions:
                # if the user doesn't have this permission globally already
                if not self.request.user.has_perm(permission):
                    # then assign it for this object
                    assign(permission, self.request.user, self.object)

        return obj

    def get_context_data(self, **kwargs):
        context = super(SmartModelFormView, self).get_context_data(**kwargs)
        context['javascript_submit'] = self.javascript_submit
        return context

class SmartUpdateView(SmartModelFormView, UpdateView):
    default_template = 'smartmin/update.html'
    exclude = ('created_by', 'modified_by')
    submit_button_name = "Save Changes"

    # allows you to specify the name of URL to use for a remove link that will automatically be shown
    delete_url = None

    @classmethod
    def derive_url_pattern(cls, path, action):
        """
        Returns the URL pattern for this view.
        """
        return r'^%s/%s/(?P<pk>\d+)/$' % (path, action)

    def derive_success_message(self):
        # first check whether a default message has been set
        if self.success_message:
            return self.success_message
        else:
            return "Your %s has been updated." % self.model._meta.verbose_name

    def pre_save(self, obj):
        # auto populate modified_by if it is present
        if hasattr(obj, 'modified_by_id') and self.request.user.id >= 0:
            obj.modified_by = self.request.user

        return obj

    def get_context_data(self, **kwargs):
        context = super(SmartUpdateView, self).get_context_data(**kwargs)

        if self.delete_url:
            context['delete_url'] = smart_url(self.delete_url, self.object.id)
            
        return context

    def get_modified_blurb(self, obj):
        return "%s by %s" % (obj.modified_on.strftime("%B %d, %Y at %I:%M %p"), obj.modified_by)

    def get_created_blurb(self, obj):
        return "%s by %s" % (obj.created_on.strftime("%B %d, %Y at %I:%M %p"), obj.created_by)

class SmartMultiFormView(SmartView, TemplateView):
    default_template = 'smartmin/multi_form.html'
    forms = {}

    # allows you to specify the name of URL to use for a remove link that will automatically be shown
    delete_url = None

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        page_forms = []
        for prefix, form in self.forms.items():
            f = form(prefix=prefix)
            page_forms.append(f)

        context['forms'] = page_forms

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        # process our forms
        page_forms = []
        valid = True
        for prefix, form in self.forms.items():
            f = form(request.POST, prefix=prefix)
            valid = valid and f.is_valid()
            page_forms.append(f)

        if not valid:
            context['forms'] = page_forms
            return self.render_to_response(context)
        else:
            # redirect to success page
            pass

    def get_context_data(self, **kwargs):
        context = super(SmartMultiFormView, self).get_context_data(**kwargs)

        if self.delete_url:
            context['delete_url'] = smart_url(self.delete_url, self.object.id)
            
        return context

class SmartCreateView(SmartModelFormView, CreateView):
    default_template = 'smartmin/create.html'
    exclude = ('created_by', 'modified_by', 'is_active')
    submit_button_name = "Create"

    def pre_save(self, obj):
        # auto populate created_by if it is present
        if hasattr(obj, 'created_by_id') and self.request.user.id >= 0:
            obj.created_by = self.request.user

        # auto populate modified_by if it is present
        if hasattr(obj, 'modified_by_id') and self.request.user.id >= 0:
            obj.modified_by = self.request.user            

        return obj

    def derive_success_message(self):
        # first check whether a default message has been set
        if self.success_message:
            return self.success_message
        else:
            return "Your new %s has been created." % self.model._meta.verbose_name

    def derive_title(self):
        """
        Derives our title from our object
        """
        if not self.title:
            return "Create %s" % force_unicode(self.model._meta.verbose_name).title()
        else:
            return self.title

class SmartCRUDL(object):
    actions = ('create', 'read', 'update', 'delete', 'list')
    model_name = None
    app_name = None
    module_name = None
    path = None
    
    permissions = False

    def __init__(self, model=None, path=None, actions=None):
        # set our model if passed in
        if model:
            self.model = model

        # derive our model name
        if not self.model_name:
            self.model_name = self.model._meta.object_name

        # derive our app name
        # TODO: we should really be using the module name here, not the model's app name to allow
        #       for apps to easily reuse objects from different apps.
        if not self.app_name:
            self.app_name = self.model._meta.app_label

        # derive our path from our class name
        if not path and not self.path:
            self.path = self.model_name.lower()

        # derive our module name from our class's module
        if not self.module_name:
            self.module_name = self.__class__.__module__.split(".")[0]

        # set our actions if set
        if actions:
            self.actions = actions

    def permission_for_action(self, action):
        """
        Returns the permission to use for the passed in action
        """
        return "%s.%s_%s" % (self.app_name.lower(), self.model_name.lower(), action)

    def template_for_action(self, action):
        """
        Returns the template to use for the passed in action
        """
        return "%s/%s_%s.html" % (self.app_name.lower(), self.model_name.lower(), action)

    def url_name_for_action(self, action):
        """
        Returns the permission to use for the passed in action
        """
        return "%s.%s_%s" % (self.module_name, self.model_name.lower(), action)        

    def view_for_action(self, action):
        """
        Returns the appropriate view class for the passed in action
        """
        # this turns replace_foo into ReplaceFoo and read into Read
        class_name = "".join([word.capitalize() for word in action.split("_")])
        view = None

        # see if we have a custom class defined for this action
        if hasattr(self, class_name):
            # return that one
            view = getattr(self, class_name)

            # no model set?  set it ourselves
            if not getattr(view, 'model', None):
                view.model = self.model

            # no permission and we are supposed to set them, do so
            if not hasattr(view, 'permission') and self.permissions:
                view.permission = self.permission_for_action(action)

            # set our link URL based on read and update
            if not getattr(view, 'link_url', None):
                if 'read' in self.actions:
                    view.link_url = "id@%s.%s_read" % (self.module_name, self.model_name.lower())
                elif 'update' in self.actions:
                    view.link_url = "id@%s.%s_update" % (self.module_name, self.model_name.lower())
                else:
                    view.link_fields = ()

            # set add_button based on existance of Create view if add_button not explicitely set
            if not getattr(view, 'add_button', None) and (action == 'list' and 'create' in self.actions):
                view.add_button = True

            # set edit_button based on existance of Update view if edit_button not explicitely set
            if not getattr(view, 'edit_button', None) and (action == 'read' and 'update' in self.actions):
                view.edit_button = True

            # if update or create, set success url if not set
            if not getattr(view, 'success_url', None) and (action == 'update' or action == 'create'):
                view.success_url = "@%s.%s_list" % (self.module_name, self.model_name.lower())

        # otherwise, use our defaults
        else:
            options = dict(model=self.model)

            # if this is an update or create, and we have a list view, then set the default to that
            if action == 'update' or action == 'create' and 'list' in self.actions:
                options['success_url'] = "@%s.%s_list" % (self.module_name, self.model_name.lower())

            # set permissions if appropriate
            if self.permissions:
                options['permission'] = self.permission_for_action(action)
            
            if action == 'create':
                view = type("%sCreateView" % self.model_name, (SmartCreateView,),
                            options)

            elif action == 'read':
                if 'update' in self.actions:
                    options['edit_button'] = True

                view = type("%sReadView" % self.model_name, (SmartReadView,),
                            options)

            elif action == 'update':
                if 'delete' in self.actions:
                    options['delete_url'] = "id@%s.%s_delete" % (self.module_name, self.model_name.lower())
                
                view = type("%sUpdateView" % self.model_name, (SmartUpdateView,),
                            options)

            elif action == 'delete':
                if 'list' in self.actions:
                    options['cancel_url'] = "@%s.%s_list" % (self.module_name, self.model_name.lower())
                    options['redirect_url'] = "@%s.%s_list" % (self.module_name, self.model_name.lower())
                
                view = type("%sDeleteView" % self.model_name, (SmartDeleteView,),
                            options)

            elif action == 'list':
                if 'read' in self.actions:
                    options['link_url'] = "id@%s.%s_read" % (self.module_name, self.model_name.lower())
                elif 'update' in self.actions:
                    options['link_url'] = "id@%s.%s_update" % (self.module_name, self.model_name.lower())
                else:
                    options['link_fields'] = ()

                if 'create' in self.actions:
                    options['add_button'] = True
                
                view = type("%sListView" % self.model_name, (SmartListView,),
                            options)

        if not view:
            # couldn't find a view?  blow up
            raise Exception("No view found for action: %s" % action)

        # set the url name for this view
        view.url_name = self.url_name_for_action(action)

        # no template set for it?  set one based on our action and app name
        if not getattr(view, 'template_name', None):
            view.template_name = self.template_for_action(action)

        return view

    def pattern_for_view(self, view, action):
        """
        Returns the URL pattern for the passed in action.
        """
        # if this view knows how to define a URL pattern, call that
        if getattr(view, 'derive_url_pattern', None):
            return view.derive_url_pattern(self.path, action)

        # otherwise take our best guess
        else:
            return r'^%s/%s/$' % (self.path, action)            

    def as_urlpatterns(self):
        """
        Creates the appropriate URL patterns for this object.
        """
        urlpatterns = patterns('')
        
        # for each of our actions
        for action in self.actions:
            view_class = self.view_for_action(action)
            view_pattern = self.pattern_for_view(view_class, action)
            name = self.url_name_for_action(action)
            urlpatterns += patterns('', url(view_pattern, view_class.as_view(), name=name))

        return urlpatterns




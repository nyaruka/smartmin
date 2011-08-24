
# simple mixins that keep you from writing so much code
class PassRequestToFormMixin(object):
    def get_form_kwargs(self):
        kwargs = super(PassRequestToFormMixin, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

from __future__ import unicode_literals

import random
import string

from datetime import timedelta
from django import forms
from django.conf import settings
from django.contrib import messages, auth
from django.contrib.auth import get_user_model, REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.contrib.auth.views import login as django_login
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template import loader
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView
from smartmin.email import build_email_context
from smartmin.views import SmartCRUDL, SmartView, SmartFormView, SmartListView, SmartCreateView, SmartUpdateView
from .models import RecoveryToken, PasswordHistory, FailedLogin, is_password_complex


class UserForm(forms.ModelForm):
    new_password = forms.CharField(label=_("New Password"), widget=forms.PasswordInput)
    groups = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                                            queryset=Group.objects.all(), required=False)

    def clean_new_password(self):
        password = self.cleaned_data['new_password']

        # if they specified a new password
        if password and not is_password_complex(password):
            raise forms.ValidationError(_("Passwords must have at least 8 characters, including one uppercase, "
                                          "one lowercase and one number"))

        return password

    def save(self, commit=True):
        """
        Overloaded so we can save any new password that is included.
        """
        is_new_user = self.instance.pk is None

        user = super(UserForm, self).save(commit)

        # new users should be made active by default
        if is_new_user:
            user.is_active = True

        # if we had a new password set, use it
        new_pass = self.cleaned_data['new_password']
        if new_pass:
            user.set_password(new_pass)
            if commit:
                user.save()

        return user

    class Meta:
        model = get_user_model()
        fields = ('username', 'new_password', 'first_name', 'last_name', 'email', 'groups', 'is_active')


class UserUpdateForm(UserForm):
    new_password = forms.CharField(label=_("New Password"), widget=forms.PasswordInput, required=False)

    def clean_new_password(self):
        password = self.cleaned_data['new_password']

        if password and not is_password_complex(password):
            raise forms.ValidationError(_("Passwords must have at least 8 characters, including one uppercase, "
                                          "one lowercase and one number"))

        if password and PasswordHistory.is_password_repeat(self.instance, password):
            raise forms.ValidationError(_("You have used this password before in the past year, "
                                          "please use a new password."))

        return password


class UserProfileForm(UserForm):
    old_password = forms.CharField(label=_("Password"), widget=forms.PasswordInput, required=False)
    new_password = forms.CharField(label=_("New Password"), widget=forms.PasswordInput, required=False)
    confirm_new_password = forms.CharField(label=_("Confirm Password"), widget=forms.PasswordInput, required=False)

    def clean_old_password(self):
        user = self.instance

        if(not user.check_password(self.cleaned_data['old_password'])):
            raise forms.ValidationError(_("Please enter your password to save changes."))

        return self.cleaned_data['old_password']

    def clean_confirm_new_password(self):
        if 'new_password' not in self.cleaned_data:
            return None

        if not self.cleaned_data['confirm_new_password'] and self.cleaned_data['new_password']:
            raise forms.ValidationError(_("Confirm the new password by filling the this field"))

        if self.cleaned_data['new_password'] != self.cleaned_data['confirm_new_password']:
            raise forms.ValidationError(_("New password doesn't match with its confirmation"))

        password = self.cleaned_data['new_password']
        if password and not is_password_complex(password):
            raise forms.ValidationError(_("Passwords must have at least 8 characters, including one uppercase, "
                                          "one lowercase and one number"))

        if password and PasswordHistory.is_password_repeat(self.instance, password):
            raise forms.ValidationError(_("You have used this password before in the past year, "
                                          "please use a new password."))

        return self.cleaned_data['new_password']


class UserForgetForm(forms.Form):
    email = forms.EmailField(label=_("Your Email"),)

    def clean_email(self):
        email = self.cleaned_data['email'].strip()

        allow_email_recovery = getattr(settings, 'USER_ALLOW_EMAIL_RECOVERY', True)
        if not allow_email_recovery:
            raise forms.ValidationError(_("E-mail recovery is not supported, "
                                          "please contact the website administrator to reset your password manually."))

        return email


class SetPasswordForm(UserForm):
    old_password = forms.CharField(label=_("Current Password"), widget=forms.PasswordInput, required=True,
                                   help_text=_("Your current password"))
    new_password = forms.CharField(label=_("New Password"), widget=forms.PasswordInput, required=True,
                                   help_text=_("Your new password."))
    confirm_new_password = forms.CharField(label=_("Confirm new Password"), widget=forms.PasswordInput, required=True,
                                           help_text=_("Confirm your new password."))

    def clean_old_password(self):
        user = self.instance
        if not user.check_password(self.cleaned_data['old_password']):
            raise forms.ValidationError(_("Please enter your password to save changes"))

        return self.cleaned_data['old_password']

    def clean_confirm_new_password(self):
        if 'new_password' not in self.cleaned_data:
            return None

        if not self.cleaned_data['confirm_new_password'] and self.cleaned_data['new_password']:
            raise forms.ValidationError(_("Confirm your new password by entering it here"))

        if self.cleaned_data['new_password'] != self.cleaned_data['confirm_new_password']:
            raise forms.ValidationError(_("Mismatch between your new password and confirmation, try again"))

        password = self.cleaned_data['new_password']
        if password and not is_password_complex(password):
            raise forms.ValidationError(_("Passwords must have at least 8 characters, including one uppercase, "
                                          "one lowercase and one number"))

        if password and PasswordHistory.is_password_repeat(self.instance, password):
            raise forms.ValidationError(_("You have used this password before in the past year, "
                                          "please use a new password."))

        return self.cleaned_data['new_password']


class UserCRUDL(SmartCRUDL):
    model = get_user_model()
    permissions = True
    actions = ('create', 'list', 'update', 'profile', 'forget', 'recover', 'expired', 'failed', 'newpassword', 'mimic')

    class List(SmartListView):
        search_fields = ('username__icontains', 'first_name__icontains', 'last_name__icontains')
        fields = ('username', 'name', 'group', 'last_login')
        link_fields = ('username', 'name')
        default_order = 'username'
        add_button = True
        template_name = "smartmin/users/user_list.html"

        def get_context_data(self, **kwargs):
            context = super(UserCRUDL.List, self).get_context_data(**kwargs)
            context['groups'] = Group.objects.all()
            group_id = self.request.POST.get('group_id', self.request.GET.get('group_id', 0))
            context['group_id'] = int(group_id)
            return context

        def get_group(self, obj):
            return ", ".join([group.name for group in obj.groups.all()])

        def get_queryset(self, **kwargs):
            queryset = super(UserCRUDL.List, self).get_queryset(**kwargs)
            group_id = self.request.POST.get('group_id', self.request.GET.get('group_id', 0))
            group_id = int(group_id)

            # filter by the group
            if group_id:
                queryset = queryset.filter(groups=group_id)

            # ignore superusers and staff users
            return queryset.exclude(is_staff=True).exclude(is_superuser=True).exclude(password=None)

        def get_name(self, obj):
            return obj.get_full_name()

    class Create(SmartCreateView):
        form_class = UserForm
        fields = ('username', 'new_password', 'first_name', 'last_name', 'email', 'groups')
        success_message = _("New user created successfully.")

        field_config = {
            'groups': dict(label=_("Groups"),
                           help=_("Users will only get those permissions that are allowed for their group.")),
            'new_password': dict(label=_("Password"), help=_("Set the user's initial password here.")),
        }

        def post_save(self, obj):
            """
            Make sure our groups are up to date
            """
            if 'groups' in self.form.cleaned_data:
                for group in self.form.cleaned_data['groups']:
                    obj.groups.add(group)

            return obj

    class Update(SmartUpdateView):
        form_class = UserUpdateForm
        template_name = "smartmin/users/user_update.html"
        success_message = "User saved successfully."
        fields = ('username', 'new_password', 'first_name', 'last_name', 'email', 'groups', 'is_active', 'last_login')
        field_config = {
            'last_login': dict(readonly=True, label=_("Last Login")),
            'is_active': dict(label=_("Is Active"), help=_("Whether this user is allowed to log into the site")),
            'groups': dict(label=_("Groups"),
                           help=_("Users will only get those permissions that are allowed for their group")),
            'new_password': dict(label=_("New Password"),
                                 help=_("You can reset the user's password by entering a new password here")),
        }

        def post_save(self, obj):
            """
            Make sure our groups are up to date
            """
            if 'groups' in self.form.cleaned_data:
                obj.groups.clear()
                for group in self.form.cleaned_data['groups']:
                    obj.groups.add(group)

            # if a new password was set, reset our failed logins
            if 'new_password' in self.form.cleaned_data and self.form.cleaned_data['new_password']:
                FailedLogin.objects.filter(user=self.object).delete()
                PasswordHistory.objects.create(user=obj, password=obj.password)

            return obj

    class Profile(SmartUpdateView):
        form_class = UserProfileForm
        success_message = "User profile saved successfully."
        fields = ('username', 'old_password', 'new_password', 'confirm_new_password',
                  'first_name', 'last_name', 'email')
        field_config = {
            'username': dict(readonly=True, label=_("Username")),
            'old_password': dict(label=_("Password"), help=_("Your password")),
            'new_password': dict(label=_("New Password"), help=_("If you want to set a new password, enter it here")),
            'confirm_new_password': dict(label=_("Confirm New Password"), help=_("Confirm your new password")),
        }

        def post_save(self, obj):
            obj = super(UserCRUDL.Profile, self).post_save(obj)
            if 'new_password' in self.form.cleaned_data and self.form.cleaned_data['new_password']:
                FailedLogin.objects.filter(user=self.object).delete()
                PasswordHistory.objects.create(user=obj, password=obj.password)

            return obj

        def get_object(self, queryset=None):
            return self.request.user

        def derive_title(self):
            return _("Edit your profile")

    class Forget(SmartFormView):
        title = _("Password Recovery")
        template_name = 'smartmin/users/user_forget.html'
        form_class = UserForgetForm
        permission = None
        success_message = _("An Email has been sent to your account with further instructions.")
        success_url = "@users.user_login"
        fields = ('email', )

        def form_valid(self, form):
            email = form.cleaned_data['email']
            hostname = getattr(settings, 'HOSTNAME', self.request.get_host())

            col_index = hostname.find(':')
            domain = hostname[:col_index] if col_index > 0 else hostname

            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'website@%s' % domain)
            user_email_template = getattr(settings, "USER_FORGET_EMAIL_TEMPLATE", "smartmin/users/user_email.txt")
            no_user_email_template = getattr(settings, "NO_USER_FORGET_EMAIL_TEMPLATE",
                                             "smartmin/users/no_user_email.txt")

            email_template = loader.get_template(no_user_email_template)
            user = get_user_model().objects.filter(email__iexact=email).first()

            context = build_email_context(self.request, user)

            if user:
                token = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
                RecoveryToken.objects.create(token=token, user=user)
                email_template = loader.get_template(user_email_template)
                FailedLogin.objects.filter(user=user).delete()
                context['user'] = user
                context['path'] = "%s" % reverse('users.user_recover', args=[token])

            send_mail(_('Password Recovery Request'), email_template.render(context), from_email,
                      [email], fail_silently=False)

            response = super(UserCRUDL.Forget, self).form_valid(form)
            return response

    class Newpassword(SmartUpdateView):
        form_class = SetPasswordForm
        fields = ('old_password', 'new_password', 'confirm_new_password')
        title = _("Pick a new password")
        template_name = 'smartmin/users/user_newpassword.html'
        success_message = _("Your password has successfully been updated, thank you.")

        def get_context_data(self, *args, **kwargs):
            context_data = super(UserCRUDL.Newpassword, self).get_context_data(*args, **kwargs)
            context_data['expire_days'] = getattr(settings, 'USER_PASSWORD_EXPIRATION', -1)
            context_data['window_days'] = getattr(settings, 'USER_PASSWORD_REPEAT_WINDOW', -1)
            return context_data

        def has_permission(self, request, *args, **kwargs):
            return request.user.is_authenticated()

        def get_object(self, queryset=None):
            return self.request.user

        def post_save(self, obj):
            obj = super(UserCRUDL.Newpassword, self).post_save(obj)
            PasswordHistory.objects.create(user=obj, password=obj.password)
            return obj

        def get_success_url(self):
            return settings.LOGIN_REDIRECT_URL

    class Mimic(SmartUpdateView):
        fields = ('id',)

        def derive_success_message(self):
            return _("You are now logged in as %s") % self.object.username

        def pre_process(self, request, *args, **kwargs):
            user = self.get_object()
            login(request)

            # After logging in it is important to change the user stored in the session
            # otherwise the user will remain the same
            request.session[auth.SESSION_KEY] = user.id
            request.session[auth.HASH_SESSION_KEY] = user.get_session_auth_hash()

            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)

    class Recover(SmartUpdateView):
        form_class = SetPasswordForm
        permission = None
        success_message = _("Password Updated Successfully. Now you can log in using your new password.")
        success_url = '@users.user_login'
        fields = ('new_password', 'confirm_new_password')
        title = _("Reset your Password")
        template_name = 'smartmin/users/user_recover.html'

        @classmethod
        def derive_url_pattern(cls, path, action):
            return r'^%s/%s/(?P<token>\w+)/$' % (path, action)

        def pre_process(self, request, *args, **kwargs):
            token = self.kwargs.get('token')
            validity_time = timezone.now() - timedelta(hours=48)
            recovery_token = RecoveryToken.objects.filter(created_on__gt=validity_time, token=token)
            if not recovery_token:
                messages.info(request, _("Your link has expired for security reasons. "
                                         "Please reinitiate the process by entering your email here."))
                return HttpResponseRedirect(reverse("users.user_forget"))
            return super(UserCRUDL.Recover, self).pre_process(request, args, kwargs)

        def get_object(self, queryset=None):
            token = self.kwargs.get('token')
            recovery_token = RecoveryToken.objects.get(token=token)
            return recovery_token.user

        def post_save(self, obj):
            obj = super(UserCRUDL.Recover, self).post_save(obj)
            validity_time = timezone.now() - timedelta(hours=48)
            RecoveryToken.objects.filter(user=obj).delete()
            RecoveryToken.objects.filter(created_on__lt=validity_time).delete()
            PasswordHistory.objects.create(user=obj, password=obj.password)
            return obj

    class Expired(SmartView, TemplateView):
        permission = None
        template_name = 'smartmin/users/user_expired.html'

    class Failed(SmartView, TemplateView):
        permission = None
        template_name = 'smartmin/users/user_failed.html'

        def get_context_data(self, *args, **kwargs):
            context = super(UserCRUDL.Failed, self).get_context_data(*args, **kwargs)

            lockout_timeout = getattr(settings, 'USER_LOCKOUT_TIMEOUT', 10)
            failed_login_limit = getattr(settings, 'USER_FAILED_LOGIN_LIMIT', 5)
            allow_email_recovery = getattr(settings, 'USER_ALLOW_EMAIL_RECOVERY', True)

            context['lockout_timeout'] = lockout_timeout
            context['failed_login_limit'] = failed_login_limit
            context['allow_email_recovery'] = allow_email_recovery

            return context


def login(request, template_name='smartmin/users/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          current_app=None, extra_context=None):

    lockout_timeout = getattr(settings, 'USER_LOCKOUT_TIMEOUT', 10)
    failed_login_limit = getattr(settings, 'USER_FAILED_LOGIN_LIMIT', 5)
    allow_email_recovery = getattr(settings, 'USER_ALLOW_EMAIL_RECOVERY', True)

    if request.method == "POST":
        if 'username' in request.POST and 'password' in request.POST:
            username = request.POST['username']

            user = get_user_model().objects.filter(username__iexact=username).first()

            # this could be a valid login by a user
            if user:

                # incorrect password?  create a failed login token
                valid_password = user.check_password(request.POST['password'])
                if not valid_password:
                    FailedLogin.objects.create(user=user)

                bad_interval = timezone.now() - timedelta(minutes=lockout_timeout)
                failures = FailedLogin.objects.filter(user=user)

                # if the failures reset after a period of time, then limit our query to that interval
                if lockout_timeout > 0:
                    failures = failures.filter(failed_on__gt=bad_interval)

                # if there are too many failed logins, take them to the failed page
                if len(failures) >= failed_login_limit:
                    return HttpResponseRedirect(reverse('users.user_failed'))

                # delete failed logins if the password is valid
                elif valid_password:
                    FailedLogin.objects.filter(user=user).delete()

    return django_login(request, template_name='smartmin/users/login.html',
                        redirect_field_name=REDIRECT_FIELD_NAME,
                        authentication_form=AuthenticationForm,
                        current_app=None, extra_context=dict(allow_email_recovery=allow_email_recovery))

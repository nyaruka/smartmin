from django.contrib.auth.models import User, Group
from django.contrib.auth.views import login as django_login
from django import forms
from django.conf import settings
from .models import *
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm

from django.shortcuts import render
from django.core.mail import send_mail
import random
import string
import datetime

from django.template import loader, Context
from smartmin.views import *

import re


class UserForm(forms.ModelForm):
    new_password = forms.CharField(label="New Password", widget=forms.PasswordInput)
    groups = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=Group.objects.all())

    def clean_new_password(self):
        password = self.cleaned_data['new_password']

        # if they specified a new password
        if password:
            has_caps = re.search('[A-Z]+', password)
            has_lower = re.search('[a-z]+', password)
            has_digit = re.search('[0-9]+', password)

            # check the complexity of the password
            if len(password) < 8 or (len(password) < 12 and (not has_caps or not has_lower or not has_digit)):
                raise forms.ValidationError("Passwords must have at least 8 characters, including one uppercase, one lowercase and one number")

        return password

    def clean_email(self):
        email = self.cleaned_data['email']
        
        if email:
            email = email.strip()

            # does another user exist with this email?
            existing = User.objects.filter(email=email)
            if existing and existing[0].pk != self.instance.pk:
                raise forms.ValidationError("That email address is already in use by another user")

        return email

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
            if commit: user.save()

        return user
    class Meta:
        model = User
        fields = ('username', 'new_password', 'first_name', 'last_name', 'email', 'groups', 'is_active')

class UserUpdateForm(UserForm):
    new_password = forms.CharField(label="New Password", widget=forms.PasswordInput, required=False)

class UserProfileForm(UserForm):
    old_password = forms.CharField(label="Password", widget=forms.PasswordInput, required=False)
    new_password = forms.CharField(label="New Password", widget=forms.PasswordInput, required=False)
    confirm_new_password = forms.CharField(label="Confirm Password", widget=forms.PasswordInput, required=False)

    def clean_old_password(self):
        user = self.instance

        if(not user.check_password(self.cleaned_data['old_password'])):
            raise forms.ValidationError("Please enter your password to save changes.")

        return self.cleaned_data['old_password']

    def clean_confirm_new_password(self):
        if not 'new_password' in self.cleaned_data:
            return None

        if(not self.cleaned_data['confirm_new_password'] and self.cleaned_data['new_password']):
            raise forms.ValidationError("Confirm the new password by filling the this field")

        if(self.cleaned_data['new_password'] != self.cleaned_data['confirm_new_password']):
            raise forms.ValidationError("New password doesn't match with its confirmation")
        return self.cleaned_data['new_password']

class UserForgetForm(forms.Form):
    email = forms.EmailField(label="Your Email",)
    
class UserRecoverForm(UserForm):
    new_password = forms.CharField(label="New Password", widget=forms.PasswordInput, required=True, help_text="Your new password.")
    confirm_new_password = forms.CharField(label="Confirm new Password", widget=forms.PasswordInput, required=True, help_text="Confirm your new password.")

    def clean_confirm_new_password(self):
        if not 'new_password' in self.cleaned_data:
            return None

        if(not self.cleaned_data['confirm_new_password'] and self.cleaned_data['new_password']):
            raise forms.ValidationError("Confirm your new password by entering it here")

        if(self.cleaned_data['new_password'] != self.cleaned_data['confirm_new_password']):
            raise forms.ValidationError("Mismatch between your new password and confirmation, try again")
        return self.cleaned_data['new_password']

class UserCRUDL(SmartCRUDL):
    model = User
    permissions = True
    actions = ('create', 'list', 'update', 'profile', 'forget', 'recover','expired')

    class List(SmartListView):
        search_fields = ('username__icontains','first_name__icontains', 'last_name__icontains')
        fields = ('username', 'name', 'group', 'last_login')
        link_fields = ('username', 'name')
        default_order = 'username'
        add_button = True
        template_name = "smartmin/users/user_list.html"
        
        def get_context_data(self, **kwargs):
            context = super(UserCRUDL.List, self).get_context_data(**kwargs)
            context['groups'] = Group.objects.all()
            context['group_id'] = int(self.request.REQUEST.get('group_id', 0))
            return context

        def get_group(self, obj):
            return ", ".join([group.name for group in obj.groups.all()])

        def get_queryset(self, **kwargs):
            queryset = super(UserCRUDL.List, self).get_queryset(**kwargs)
            group_id = int(self.request.REQUEST.get('group_id', 0))

            # filter by the group
            if group_id:
                queryset = queryset.filter(groups=group_id)
                
            return queryset.filter(id__gt=0).exclude(is_staff=True).exclude(is_superuser=True).exclude(password=None)
        
        def get_name(self, obj):
            return " ".join((obj.first_name, obj.last_name))

    class Create(SmartCreateView):
        form_class = UserForm
        fields = ('username', 'new_password', 'first_name', 'last_name', 'email', 'groups')
        success_message = "New user created successfully."

        field_config = {
            'groups': dict(help="Users will only get those permissions that are allowed for their group."),
            'new_password': dict(label="Password"),
            'groups': dict(help="Users will only get those permissions that are allowed for their group."),
            'new_password': dict(help="Set the user's initial password here."),
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
        success_message = "User saved successfully."
        fields = ('username', 'new_password', 'first_name', 'last_name', 'email', 'groups', 'is_active', 'last_login')
        field_config = {
            'last_login': dict(readonly=True),
            'is_active': dict(help="Whether this user is allowed to log into the site"),
            'groups': dict(help="Users will only get those permissions that are allowed for their group"),
            'new_password': dict(help="You can reset the user's password by entering a new password here"),
        }

        def post_save(self, obj):
            """
            Make sure our groups are up to date
            """
            if 'groups' in self.form.cleaned_data:
                obj.groups.clear()
                for group in self.form.cleaned_data['groups']:
                    obj.groups.add(group)

            return obj

    class Profile(SmartUpdateView):
        form_class = UserProfileForm
        success_message = "User profile saved successfully."
        fields = ('username', 'old_password', 'new_password', 'confirm_new_password',
                  'first_name', 'last_name', 'email')
        field_config = {
            'username': dict(readonly=True),
            'old_password': dict(help="Your password"),
            'new_password': dict(help="If you want to set a new password, enter it here"),
            'confirm_new_password': dict(help="Confirm your new password"),
        }

        def has_permission(self, request, *args, **kwargs):
            has_perm = super(UserCRUDL.Profile, self).has_permission(request, *args, **kwargs)
            user = request.user

            if (not has_perm):
                if(user.pk == int(self.kwargs['pk']) and user.is_authenticated()):
                    return True
            return has_perm

        def derive_title(self):
            return "Edit your profile"

    class Forget(SmartFormView):
        title = "Password Recovery"
        template_name = '/smartmin/users/user_forget.html'
        form_class = UserForgetForm
        permission = None
        success_message = "An Email has been sent to your account with further instructions."
        success_url = "@users.user_login"
        fields = ('email', )

        def form_valid(self, form):
            email = form.cleaned_data['email']
            hostname = getattr(settings, 'HOSTNAME', 'hostname')
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'user@hostname')
            protocol = 'https' if self.request.is_secure() else 'http'

            user = User.objects.filter(email=email)
            if user:
                user = user[0]

                token = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
                RecoveryToken.objects.create(token=token,user=user)
                email_template = loader.get_template('smartmin/users/user_email.txt')
                FailureMarker.objects.filter(user=user).delete()
                context = Context(dict(website=hostname,
                                       link='%s://%s/users/user/recover/%s/' % (protocol, hostname, token)))
                user.email_user("Password Recovery", email_template.render(context) , from_email)
            else:
                email_template = loader.get_template('smartmin/users/no_user_email.txt')
                context = Context(dict(website=hostname))
                send_mail('Password Recovery Request', email_template.render(context), from_email, 
                          [email], fail_silently=False)

            response = super(UserCRUDL.Forget, self).form_valid(form)
            return response


    class Recover(SmartUpdateView):
        form_class = UserRecoverForm
        permission = None
        success_message = "Password Updated Successfully. Now you can log in using your new password."
        success_url = '@users.user_login'
        fields = ('new_password', 'confirm_new_password')
        title = "Reset your Password"

        def pre_process(self, request, *args, **kwargs):
            token = self.kwargs.get('token')
            validity_time = datetime.datetime.now() - datetime.timedelta(hours=48)
            recovery_token = RecoveryToken.objects.filter(created_on__gt=validity_time).filter(token=token)
            if not recovery_token:
                return HttpResponseRedirect(reverse("users.user_expired"))
            return super(UserCRUDL.Recover, self).pre_process(request, args, kwargs)

        
        def get_object(self, queryset=None):
            token = self.kwargs.get('token')
            recovery_token= RecoveryToken.objects.get(token=token)
            return recovery_token.user

 
        def post_save(self, obj):
            validity_time = datetime.datetime.now() - datetime.timedelta(hours=48)
            obj = super(UserCRUDL.Recover, self).post_save(obj)
            RecoveryToken.objects.filter(user=obj).delete()
            RecoveryToken.objects.filter(created_on__lt=validity_time).delete()
            return obj


    class Expired(SmartView, TemplateView):
        permission = None
        template_name = 'smartmin/users/user_expired.html'



def login(request, template_name='smartmin/users/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          current_app=None, extra_context=None):

    time_interval = 10
    limit_attempts = 5

    if request.method == "POST":
        
        if 'username' in request.REQUEST and 'password' in request.REQUEST:

            username = request.REQUEST['username']
            user = User.objects.get(username=username)
            FailureMarker.objects.create(user=user)

        
        
    
            bad_interval = datetime.datetime.now() - datetime.timedelta(minutes=time_interval)
            failures = FailureMarker.objects.filter(user=user).filter(failed_on__gt=bad_interval)

            if len(failures) <= limit_attempts:
                return django_login(request, template_name='smartmin/users/login.html',
                                    redirect_field_name=REDIRECT_FIELD_NAME,
                                    authentication_form=AuthenticationForm,
                                    current_app=None, extra_context=None)
    

            return render(request, "smartmin/users/failure.html",dict(time_interval=time_interval,limit_attempts=limit_attempts))


    return django_login(request, template_name='smartmin/users/login.html',
                        redirect_field_name=REDIRECT_FIELD_NAME,
                        authentication_form=AuthenticationForm,
                        current_app=None, extra_context=None)

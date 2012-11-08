from django.contrib.auth.models import User, Group
from django import forms
from .models import *

from django.core.mail import send_mail
import random
import string
import datetime

from django.template import loader, Context
from smartmin.views import *

class UserForm(forms.ModelForm):
    new_password = forms.CharField(label="New Password", widget=forms.PasswordInput)
    groups = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, queryset=Group.objects.all())

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
    old_password = forms.CharField(label="Old Password", widget=forms.PasswordInput, required=False)
    new_password = forms.CharField(label="New Password", widget=forms.PasswordInput, required=False)
    confirm_new_password = forms.CharField(label="Confirm new Password", widget=forms.PasswordInput, required=False)

    def clean_old_password(self):
        user = self.instance

        if(self.cleaned_data['old_password'] and self.cleaned_data['new_password']):
            if(not user.check_password(self.cleaned_data['old_password'])):
                raise forms.ValidationError("The old password is not correct.")
        elif(self.cleaned_data['old_password'] and not self.cleaned_data['new_password']):
            raise forms.ValidationError("Please enter a new password for changes to take effect")
        return self.cleaned_data['old_password']

    def clean_confirm_new_password(self):
        if(not self.cleaned_data['confirm_new_password'] and self.cleaned_data['new_password']):
            raise forms.ValidationError("Confirm the new password by filling the this field")

        if(self.cleaned_data['new_password'] != self.cleaned_data['confirm_new_password']):
            raise forms.ValidationError("New password doesn't match with its confirmation")
        return self.cleaned_data['new_password']

class UserForgetForm(forms.Form):
    email = forms.EmailField(label="Your Email",)
    
class UserRecoverForm(UserForm):
    new_password = forms.CharField(label="New Password", widget=forms.PasswordInput, required=True, help_text="You can reset your password by entering a new password here.")
    confirm_new_password = forms.CharField(label="Confirm new Password", widget=forms.PasswordInput, required=True, help_text="Confirm your new password by entering exactly the new password here.")

    def clean_confirm_new_password(self):
        if(not self.cleaned_data['confirm_new_password'] and self.cleaned_data['new_password']):
            raise forms.ValidationError("Confirm your new password by entering it here")

        if(self.cleaned_data['new_password'] != self.cleaned_data['confirm_new_password']):
            raise forms.ValidationError("New password doesn't match with its confirmation")
        return self.cleaned_data['new_password']

class UserCRUDL(SmartCRUDL):
    model = User
    permissions = True
    actions = ('create', 'list', 'update', 'profile', 'forget', 'recover')

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
            'is_active': dict(help="Whether this user is allowed to log into the site."),
            'groups': dict(help="Users will only get those permissions that are allowed for their group."),
            'new_password': dict(help="You can reset the user's password by entering a new password here."),
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
            'old_password': dict(help="To reset your password first enter the old password here."),
            'new_password': dict(help="You can reset your password by entering a new password here."),
            'confirm_new_password': dict(help="Confirm your new password by entering exactly the new password here."),
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
        form_class = UserForgetForm
        permission = None
        success_message = "An Email has beeen sent to your account."
        success_url = "users.user_login"
        fields = ('email', )

        def get_success_url(self):
            return reverse(self.success_url)

        def form_valid(self, form):
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                
                RecoveryToken.objects.filter(user=user).delete()
                token = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in \
range(32))
                RecoveryToken.objects.create(token=token,user=user)
                email_template = loader.get_template('smartmin/users/user_email.txt')
                context = Context(dict(website='http://%s' % self.request.META['HTTP_HOST'],
                                       link='http://%s/users/user/recover/%s/' % (self.request.META['HTTP_HOST'],token)))
                user.email_user("Password Recovery", email_template.render(context)\
 ,"website@klab.rw")
            except:
                email_template = loader.get_template('smartmin/users/no_user_email.txt')
                context = Context(dict(website=self.request.META['HTTP_HOST']))
                send_mail('Password Recovery Request', email_template.render(context), 'website@klab.rw', [email], fail_silently=False)

            messages.success(self.request, self.derive_success_message())
            return super(UserCRUDL.Forget, self).form_valid(form)


    class Recover(SmartUpdateView):
        form_class = UserRecoverForm
        permission = None
        success_message = "User Password Updated Successfully. Now you can login using the new password."
        success_url = '@users.user_login'
        fields = ('new_password', 'confirm_new_password')
        title = "Reset your Password"
        
        def get_object(self, queryset=None):
            token = self.kwargs.get('token')
            recovery_token= RecoveryToken.objects.get(token=token)
            return recovery_token.user




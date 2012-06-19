from django.contrib.auth.models import User, Group
from django import forms

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
        from django.contrib.auth import authenticate
        user_cache = authenticate(username=self.instance.username, password=self.data['old_password'])
        if(len(self.data['old_password']) > 0 and len(self.data['new_password']) > 0):
            if(user_cache is None):
                raise forms.ValidationError("The old password is not correct.")
        elif(len(self.data['old_password']) > 0 and len(self.data['new_password']) == 0):
            raise forms.ValidationError("Fill new password for changes to take effect")
        return self.data['old_password']

    def clean_new_password(self):
        if(self.data['new_password'] != self.data['confirm_new_password']):
            raise forms.ValidationError("New password doesn't match with its confirmation")
        return self.data['new_password']

class UserCRUDL(SmartCRUDL):
    model = User
    permissions = True
    actions = ('create', 'list', 'update', 'profile')

    class List(SmartListView):
        search_fields = ('username__icontains','first_name__icontains', 'last_name__icontains')
        fields = ('username', 'name', 'group', 'last_login')
        link_fields = ('username', 'name')
        default_order = 'username'
        add_button = True

        def get_group(self, obj):
            return ", ".join([group.name for group in obj.groups.all()])

        def get_queryset(self, **kwargs):
            queryset = super(UserCRUDL.List, self).get_queryset(**kwargs)
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
                  'first_name', 'last_name', 'email', 'groups', 'is_active')
        field_config = {
            'is_active': dict(help="Whether this user is allowed to log into the site."),
            'groups': dict(help="Users will only get those permissions that are allowed for their group."),
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

        def derive_field_config(self):
            field_config = super(UserCRUDL.Profile, self).derive_field_config()
            field_config['username'] = dict(readonly=True, help="You cannot edit your username, this right is reserved for the adminstrator")
            return field_config

        def derive_fields(self):
            fields = super(UserCRUDL.Profile, self).derive_fields()
            fields.remove('groups')
            fields.remove('is_active')
            return fields

        def post_save(self, obj):
            """
            Make sure our groups are up to date
            """
            if 'groups' in self.form.cleaned_data:
                obj.groups.clear()
                for group in self.form.cleaned_data['groups']:
                    obj.groups.add(group)

            return obj
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

class UserCRUDL(SmartCRUDL):
    model = User
    permissions = True
    actions = ('create', 'list', 'update')

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
            return queryset.filter(id__gt=0).exclude(is_staff=True).exclude(is_superuser=True)

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



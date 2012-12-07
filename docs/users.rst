
Users
================

Smartmin provides some views and utilities to facilitate managing users.  This includes views to help users when they forget their passwords, functionality to force password expiration, complexity requirements and prevent users from repeating passwords.

Configuration
======================

First and foremost, you'll want to include `smartmin.users` in your INSTALLED_APPS, and include smartmin.urls in your project urls.py.

If you intend to use the password expiration feature, you will also need to add the ChangePasswordMiddleware to your `MIDDLEWARE_CLASSES` setting `smartmin.users.middleware.ChangePasswordMiddleware`. (best if last)

The following variables can be set in your settings.py to change various behavior:

  USER_FAILED_LOGIN_LIMIT = The number of times a user can fail a login with an incorrect password before being locked out.  (default value is 5)

  USER_LOCKOUT_TIMEOUT = The number of minutes that a user must wait before trying to log in again after reaching the limit above.  If set to -1 or 0, the user is permanently locked out until an administrator resets the password.  (default value is 10)

  USER_ALLOW_EMAIL_RECOVERY = Whether users are able to recover their password via a token sent to their email address.  (default is True)

  USER_PASSWORD_EXPIRATION = How many days before a user's password expires and they need to choose a new one. If set to 0 or a negative value then there is no expiration. (default is -1)

  USER_PASSWORD_REPEAT_WINDOW = The window whereby past passwords must not repeat.  For example, if set to 365, users will not be able to set a password that has been used in the past year.  If set to 0 or a negative value, then no enforcement of repetition is made. (default is -1)




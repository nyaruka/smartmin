HTML5 Boilerplate
===========================================

Smartmin comes ready to go straight out the box, including using a recent version of the most excellent HTML5 boilerplate so you can build a standards compliant and optimized website.

File Layout
===========================================

Again, Smartmin defines a layout for your files, things will just be easier if you agree::

  /static/ - all static files

    /css/  - any css stylesheets
      reset.css - this is the HTML5 boilerplate reset
      smartmin_styles.css - styles specific to smartmin functionality
      styles.css - this can be any of your custom styles

    /img/ - any static images

    /js/ - your javascript files
      /libs/ - external javascript libraries you depend on

Blocks
===========================================

All pages rendered by smartmin inherit from the ``base.html``, which contains the following blocks:

title
        This is the title of the page displayed in the ``<title>`` tag

extrastyle
        Any extra stylesheets or CSS you want to include on your page.  Surround either in ``<style>`` or ``<link>``

login
        The login block, will either display a login link or the name of the logged in user with a logout link

messages
        Any messages, or 'flashes', pushed in by the view.

content
        The primary content block of the page, this is the main body.

footer 
        Any footer treatment.

extrascript
        Any extra javascript you wanted included, this is put at the bottom of the page


Customizing
=============================================

You can, and shoud customize the ``base.html`` to your needs.  The only thing smartmin depends on is having the content, extrascript and extrastyle blocks available.


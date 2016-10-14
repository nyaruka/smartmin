from __future__ import unicode_literals

__version__ = '1.9.1'


def class_from_string(class_name):
    """
    Used to load a class object dynamically by name
    """
    parts = class_name.split('.')
    module = ".".join(parts[:-1])
    m = __import__(module)
    for comp in parts[1:]:
        m = getattr(m, comp)
    return m

"""
WSGI config for chatbot project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

# Set the default settings module for the 'chatbot' project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot.settings')

# Create the WSGI application object
application = get_wsgi_application()

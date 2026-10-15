"""
WSGI config for __PROJECT_NAME__ project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "__CONF_PACKAGE__.settings")

application = get_wsgi_application()

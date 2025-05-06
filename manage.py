#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    # Set the default Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mamamind.settings")

    # Check if the environment is set to 'production', and if so, load the production settings
    if os.environ.get("DJANGO_ENV") == "production":
        os.environ["DJANGO_SETTINGS_MODULE"] = "mamamind.settings.production"

    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        try:
            import django
            django.setup()
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable?"
            )
    execute_from_command_line(sys.argv)

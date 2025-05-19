from __future__ import absolute_import, unicode_literals

# This shim imports the Celery app from your hyphenated project directory
from importlib import import_module

# Import the actual celery app from the hyphenated folder
mama_mind = import_module("mama-mind-.celery")

app = mama_mind.app

#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from dotenv import load_dotenv

load_dotenv()  # load .env so DJANGO_SECRET_KEY etc. are available


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "devassist.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH? Did you activate a virtual env?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

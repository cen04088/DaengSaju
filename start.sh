#!/bin/bash
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py refresh_compatibility_copy
gunicorn config.wsgi --log-file -

#!/bin/bash
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py refresh_compatibility_copy
python manage.py normalize_copy_tone
gunicorn config.wsgi --log-file -

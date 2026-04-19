#!/bin/bash
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py loaddata full_saju_data.json
gunicorn config.wsgi --log-file -

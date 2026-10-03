web: python manage.py migrate --no-input && python manage.py refresh_compatibility_copy && python manage.py collectstatic --no-input && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT

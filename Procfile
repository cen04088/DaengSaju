web: gunicorn config.wsgi --log-file -
-release: python manage.py migrate
+release: python manage.py migrate && python manage.py loaddata saju_data.json

import os
from django.apps import AppConfig

class SajuConfig(AppConfig):
    name = 'saju'

    def ready(self):
        # 런서버(watch mode) 실행 시 이중 실행되는 것을 방지
        run_main = os.environ.get('RUN_MAIN', None)
        if run_main == 'true' or not os.environ.get('DJANGO_SETTINGS_MODULE'):
            try:
                from . import cron
                cron.start_scheduler()
            except BaseException:
                pass

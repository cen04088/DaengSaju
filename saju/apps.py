import os

from django.apps import AppConfig


class SajuConfig(AppConfig):
    name = 'saju'

    def ready(self):
        if os.environ.get('ENABLE_APSCHEDULER', 'false').lower() != 'true':
            return

        run_main = os.environ.get('RUN_MAIN')
        if run_main == 'false':
            return

        try:
            from . import cron
            cron.start_scheduler()
        except Exception:
            pass

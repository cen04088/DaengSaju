import os
from django.apps import AppConfig

class SajuConfig(AppConfig):
    name = 'saju'

    def ready(self):
        # runserver(개발) 환경: RUN_MAIN='true'일 때만 실행 (이중 실행 방지)
        # gunicorn(배포) 환경: RUN_MAIN이 없으므로 그냥 실행
        run_main = os.environ.get('RUN_MAIN')
        if run_main != 'false':  # 'false'가 아닌 경우 모두 실행 (None, 'true' 포함)
            try:
                from . import cron
                cron.start_scheduler()
            except Exception:
                pass

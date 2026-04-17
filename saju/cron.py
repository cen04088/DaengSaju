from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import register_events, DjangoJobStore
import logging
from datetime import date
from .models import DailyElementLuck
from .services.gemini_ai import generate_daily_luck

logger = logging.getLogger(__name__)

def generate_daily_luck_cron():
    today = date.today()
    elements = ['목', '화', '토', '금', '수']
    
    # 중복 방지를 위해 기존 데이터 삭제
    DailyElementLuck.objects.filter(date=today).delete()
    
    for element in elements:
        try:
            today_str = today.strftime("%Y년 %m월 %d일")
            luck_data = generate_daily_luck(
                dog_name="[강아지이름]",
                main_element=element,
                today_date_str=today_str
            )
            DailyElementLuck.objects.create(
                date=today,
                element=element,
                luck_score=luck_data.get('luck_score', 80),
                message=luck_data.get('message', ''),
                lucky_color=luck_data.get('lucky_color', ''),
                lucky_direction=luck_data.get('lucky_direction', '')
            )
        except Exception as e:
            logger.error(f"Failed to generate daily luck for {element}: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    scheduler.add_job(
        generate_daily_luck_cron,
        trigger=CronTrigger(hour="00", minute="00"),  # Every day at midnight
        id="generate_daily_luck_job",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Added job 'generate_daily_luck_cron'.")
    
    # 켜질 때 오늘 치 데이터가 없으면 즉시 실행하도록 추가
    today = date.today()
    if not DailyElementLuck.objects.filter(date=today).exists():
        scheduler.add_job(generate_daily_luck_cron, trigger='date', id='init_daily_luck', replace_existing=True)

    try:
        logger.info("Starting scheduler...")
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Stopping scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler shut down successfully!")

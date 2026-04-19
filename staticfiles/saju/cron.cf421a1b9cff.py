import logging
import random
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import register_events, DjangoJobStore

from .models import DailyElementLuck, DailyLuckArchetype
from .services.manseryeok import get_saju_for_dog, get_relationship_type

logger = logging.getLogger(__name__)

def generate_daily_luck_cron():
    """
    매일 자정에 실행되어 5가지 오행별 오늘의 운세를 생성합니다.
    일진(오늘의 기운) + 날짜(버전 순환)를 조합하여 75가지 시나리오 중 하나를 서빙합니다.
    """
    today = date.today()
    
    # 1. 버전 결정 (날짜 기반 순환: A, B, C)
    # 1, 4, 7... -> A / 2, 5, 8... -> B / 3, 6, 9... -> C
    version_map = {1: 'A', 2: 'B', 0: 'C'}
    version = version_map.get(today.day % 3)
    
    # 2. 오늘의 기운(일진) 계산
    try:
        today_saju = get_saju_for_dog(today)
        today_element = today_saju['main_element']
        logger.info(f"오늘({today})의 기운: {today_element} / 선택 버전: {version}")
    except Exception as e:
        logger.error(f"오늘의 기운 계산 실패: {e}")
        today_element = '토'
        version = 'A'

    elements = ['목', '화', '토', '금', '수']
    
    DailyElementLuck.objects.filter(date=today).delete()
    
    for element in elements:
        try:
            # 3. 관계 계산
            rel_type = get_relationship_type(element, today_element)
            
            # 4. 해당 버전의 템플릿(Archetype) 조회
            archetype = DailyLuckArchetype.objects.filter(
                dog_element=element,
                relationship_type=rel_type,
                version=version
            ).first()
            
            # 만약 해당 버전이 아직 생성 안 되었다면 A 버전이라도 시도
            if not archetype:
                archetype = DailyLuckArchetype.objects.filter(
                    dog_element=element,
                    relationship_type=rel_type
                ).first()
            
            if archetype:
                # 5. 동적 점수 생성 (관계 기반 랜덤 범위)
                score_range = {
                    '인성': (88, 98),
                    '비겁': (82, 95),
                    '식상': (78, 92),
                    '재성': (72, 88),
                    '관성': (60, 78)
                }.get(rel_type, (70, 90))
                
                luck_score = random.randint(*score_range)
                
                DailyElementLuck.objects.create(
                    date=today,
                    element=element,
                    luck_score=luck_score,
                    message=archetype.message,
                    lucky_color=archetype.lucky_color,
                    lucky_direction=archetype.lucky_direction
                )
                logger.info(f"성공: {element} ({rel_type}-{version})")
            else:
                logger.warning(f"템플릿 전무: {element}-{rel_type}")
                DailyElementLuck.objects.create(
                    date=today,
                    element=element,
                    luck_score=80,
                    message=f"오늘은 {element} 기운의 아이들에게 특별한 에너지가 도는 날입니다! 즐겁게 산책해 보세요. 🐾",
                    lucky_color="크림색",
                    lucky_direction="모두가 즐거운 방향"
                )

        except Exception as e:
            logger.error(f"Failed to generate luck for {element}: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    scheduler.add_job(
        generate_daily_luck_cron,
        trigger=CronTrigger(hour="00", minute="00"),
        id="generate_daily_luck_job",
        max_instances=1,
        replace_existing=True,
    )
    
    # 서버 기동 시 오늘 치 데이터가 없으면 즉시 실행
    today = date.today()
    if not DailyElementLuck.objects.filter(date=today).exists():
        scheduler.add_job(generate_daily_luck_cron, trigger='date', id='init_daily_luck', replace_existing=True)

    try:
        logger.info("Starting scheduler...")
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Stopping scheduler...")
        scheduler.shutdown()

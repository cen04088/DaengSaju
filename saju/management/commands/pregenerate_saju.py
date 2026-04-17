from django.core.management.base import BaseCommand
from saju.models import ArchetypeSaju
from saju.services.gemini_ai import generate_personality

class Command(BaseCommand):
    help = '75개의 평생 사주 결과(원형)를 사전 생성합니다.'

    def handle(self, *args, **options):
        # 5가지 본질 오행
        elements = ['목', '화', '토', '금', '수']
        # 버전 A, B, C
        versions = ['A', 'B', 'C']

        self.stdout.write("평생 사주 원형 생성 시작...")

        total_created = 0

        for primary in elements:
            for strongest in elements:
                for version in versions:
                    # 매번 약간씩 다른 결과를 유도하기 위해 버전마다 문맥을 추가
                    if ArchetypeSaju.objects.filter(primary_element=primary, strongest_element=strongest, version=version).exists():
                        continue
                    
                    self.stdout.write(f"[{version}] {primary}/{strongest} 생성 중...")
                    
                    placeholder_name = "[강아지이름]"
                    dist = {'목': 10, '화': 10, '토': 10, '금': 10, '수': 10}
                    dist[strongest] = 60
                    
                    data = generate_personality(
                        dog_name=placeholder_name,
                        main_element=primary,
                        element_dist=dist,
                        saju_text=f"전체적으로 {strongest} 기운이 강하며, 버전 {version} 스타일로 매우 다채롭게 묘사해주세요."
                    )
                    
                    ArchetypeSaju.objects.create(
                        primary_element=primary,
                        strongest_element=strongest,
                        version=version,
                        personality_summary=data.get('personality_summary', ''),
                        personality_keywords=data.get('personality_keywords', []),
                        vitality_analysis=data.get('vitality_analysis', ''),
                        social_analysis=data.get('social_analysis', ''),
                        treat_luck=data.get('treat_luck', ''),
                        care_tips=data.get('care_tips', '')
                    )
                    total_created += 1
        
        self.stdout.write(self.style.SUCCESS(f"완료! 총 {total_created}개 신규 생성됨."))

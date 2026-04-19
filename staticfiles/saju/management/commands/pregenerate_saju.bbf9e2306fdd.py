import time
import sys
import io
from django.core.management.base import BaseCommand
from saju.models import ArchetypeSaju
from saju.services.gemini_ai import generate_personality

# 십성 유형별 명리학적 의미 설명 (Gemini 프롬프트 보강용)
RELATIONSHIP_DESCRIPTIONS = {
    '비겁': "본질(일간) 오행과 주변에서 가장 강한 오행이 동일합니다(比劫). 같은 기운이 겹쳐 에너지가 강렬하고 독립심이 강하며, 자기 영역 의식이 뚜렷한 경향이 있습니다.",
    '인성': "주변에서 가장 강한 기운이 본질(일간) 오행을 生해주는 인성(印星) 관계입니다. 마치 어머니 품처럼 주변의 에너지가 나를 도와주어, 의존적이지만 따뜻하고 감수성이 풍부한 기질입니다.",
    '식상': "본질(일간) 오행이 주변에서 가장 강한 기운을 生해주는 식상(食傷) 관계입니다. 내가 에너지를 주변에 나눠주는 구조여서, 표현력이 풍부하고 창의적이며 타인과의 교류를 즐기는 기질입니다.",
    '재성': "본질(일간) 오행이 주변에서 가장 강한 기운을 克하는 재성(財星) 관계입니다. 내가 주변을 지배하고 탐구하는 구조여서, 목표지향적이고 활동적이며 탐구욕이 강한 기질입니다.",
    '관성': "주변에서 가장 강한 기운이 본질(일간) 오행을 克하는 관성(官星) 관계입니다. 주변이 나를 억제하는 구조여서, 규범을 중시하고 눈치가 빠르며 관찰력이 뛰어난 기질입니다.",
}

class Command(BaseCommand):
    help = '십성(十星) 기반으로 75개의 평생 사주 결과(원형)를 사전 생성합니다.'

    def handle(self, *args, **options):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

        # 5가지 본질 오행
        elements = ['목', '화', '토', '금', '수']
        # 5가지 십성 유형
        relationship_types = ['비겁', '인성', '식상', '재성', '관성']
        # 버전 A, B, C
        versions = ['A', 'B', 'C']

        self.stdout.write("[START] 십성 기반 평생 사주 원형 생성 시작...")
        self.stdout.flush()

        total_created = 0

        for primary in elements:
            for rel_type in relationship_types:
                for version in versions:
                    if ArchetypeSaju.objects.filter(
                        primary_element=primary,
                        relationship_type=rel_type,
                        version=version
                    ).exists():
                        self.stdout.write(f"[SKIP] {primary}/{rel_type} [{version}] 이미 존재")
                        self.stdout.flush()
                        continue

                    try:
                        self.stdout.write(f"[GEN] {primary}/{rel_type} [{version}] 생성 중... (Rate Limit 방지, 8초 대기)")
                        self.stdout.flush()
                        time.sleep(8)

                        placeholder_name = "[강아지이름]"
                        # 십성 관계에 따른 오행 분포 시뮬레이션
                        dist = {'목': 10, '화': 10, '토': 10, '금': 10, '수': 10}
                        rel_desc = RELATIONSHIP_DESCRIPTIONS.get(rel_type, '')
                        
                        saju_context = (
                            f"[명리학 배경] {rel_desc} "
                            f"(버전 {version}의 관점에서 다채롭게 묘사해주세요.)"
                        )

                        data = generate_personality(
                            dog_name=placeholder_name,
                            main_element=primary,
                            element_dist=dist,
                            saju_text=saju_context
                        )

                        if "데이터를 불러오는 데 실패했어요" in data.get('vitality_analysis', ''):
                            self.stdout.write(f"[WARNING] API 한도 초과 의심. 60초 대기 후 재시도...")
                            self.stdout.flush()
                            time.sleep(60)
                            continue

                        ArchetypeSaju.objects.create(
                            primary_element=primary,
                            relationship_type=rel_type,
                            version=version,
                            personality_summary=data.get('personality_summary', ''),
                            personality_keywords=data.get('personality_keywords', []),
                            vitality_analysis=data.get('vitality_analysis', ''),
                            social_analysis=data.get('social_analysis', ''),
                            treat_luck=data.get('treat_luck', ''),
                            care_tips=data.get('care_tips', '')
                        )
                        total_created += 1
                        self.stdout.write(f"[OK] {primary}/{rel_type} [{version}] 저장 완료!")
                        self.stdout.flush()

                    except Exception as e:
                        self.stdout.write(f"[ERROR] 생성 실패: {str(e)[:80]} | 30초 대기 후 계속")
                        self.stdout.flush()
                        time.sleep(30)

        self.stdout.write(f"[DONE] 완료! 총 {total_created}개 신규 생성됨.")
        self.stdout.flush()

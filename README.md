# 🐶 댕사주 (DaengSaju)

### "우리 댕댕이의 사주팔자가 궁금하다면?"

**앱인토스(App in Toss)**에서 서비스 중인, 반려견의 생년월일시로 사주팔자를 계산해 성격·오늘의 운세·주인과의 궁합을 알려주는 미니앱입니다.

사람의 사주가 아니라 **강아지의 사주**를 본다는 독특한 컨셉으로, 만세력(사주) 계산 로직에 반려동물 콘텐츠를 결합했습니다.

---

## ✨ 주요 기능

### 1. 댕사주 (반려견 사주 분석)
- 강아지 이름·생년월일(음력/윤달 지원)·태어난 시간(선택)·성별 입력
- 년·월·일·시주 사주팔자 표 계산 (`sajupy` 만세력 라이브러리 기반)
- 오행(목화토금수) 밸런스를 레이더 차트 + 막대그래프로 시각화
- 활력/에너지, 사회성, 간식운, 케어팁 4가지 카테고리의 성격 리포트 제공

### 2. 댕궁합 (반려견 ↔ 주인 궁합)
- 주인의 생년월일시를 추가 입력하면, 오행 상생·상극 관계(십성)를 기반으로 궁합 점수(0~100점)와 설명, 관계 조언을 계산

### 3. 오늘의 산책운
- 매일 자정(APScheduler) 오행별 일진을 계산해, 강아지 속성에 맞는 오늘의 산책 점수·행운의 색/방향을 안내

### 4. 출석 체크 이벤트
- 월간 캘린더 기반 출석 스탬프, 1/3/5/7/10/15/20일 연속 출석 시 테마 부적 리워드 지급 (컨페티 애니메이션)

### 5. 결과 공유
- `html2canvas`로 결과 화면을 이미지로 캡처해 공유/저장

### 6. 앱인토스 사용자 연동
- 토스 웹뷰의 `X-Toss-User-Key`를 자동으로 인식해 사용자를 식별 (별도 로그인 불필요)

---

## 🛠️ 기술 스택

| 영역 | 기술 |
|---|---|
| Backend | Python, Django 6.0, Django REST Framework |
| DB | SQLite(dev) / PostgreSQL(prod, `dj-database-url`) |
| 사주 계산 | `sajupy` (만세력 계산), 커스텀 오행·십성 로직 |
| AI | Google Gemini (`gemini-2.5-flash`) — 콘텐츠 사전 생성용 |
| 스케줄링 | `django-apscheduler` (일별 오행 운세 갱신) |
| 프론트엔드 | Django Template + Vanilla JS, Chart.js, html2canvas, canvas-confetti |
| 배포 | Railway (Nixpacks + Gunicorn), Whitenoise 정적 파일 서빙 |
| 플랫폼 | 앱인토스(App in Toss) 미니앱 |

---

## 🧠 기술적으로 눈여겨볼 점 — LLM 콘텐츠 사전 생성 파이프라인

매 요청마다 LLM을 호출하면 응답 속도가 느리고 비용이 커집니다. 그래서 **"오행 × 십성 관계 × 버전"의 조합(예: 성격 유형 75종, 궁합 유형 50종, 일일 운세 75종)을 Gemini로 미리 생성해 DB에 저장**해두고, 실제 서비스에서는 캐시된 문구에 이름/조사(은·는, 이·가 등)만 자연스럽게 치환해 즉시 응답합니다.

- `saju/services/manseryeok.py` — 만세력 계산 + 오행/십성 로직 + 한국어 조사 처리 유틸
- `saju/services/gemini_ai.py` — Gemini 프롬프트 및 사전 생성 로직
- `saju/management/commands/pregenerate_*.py` — 사주/궁합/일일운세 아키타입을 배치로 채우는 관리 명령어

---

## 📁 프로젝트 구조

```
saju/
├── config/             # Django 프로젝트 설정
├── saju/               # 메인 Django 앱
│   ├── models.py        # User, Dog, SajuBasics, Archetype*, Compatibility, Attendance 등
│   ├── views.py          # DRF APIView (사주/궁합/산책운/출석 API)
│   ├── services/         # 만세력 계산, Gemini 연동
│   ├── management/commands/  # 사전 생성 배치 명령어
│   └── cron.py            # 일별 오행 운세 스케줄러
├── frontend/            # 앱인토스 등록용 Granite(React) 스캐폴드
├── index.html / app.js / style.css / assets/   # 실제 서비스 UI (Django가 서빙하는 정적 화면)
└── full_saju_data.json / saju_data.json        # 사전 생성된 아키타입 콘텐츠 fixture
```

> `frontend/` 폴더는 앱인토스 콘솔 등록을 위한 공식 Granite 템플릿이며, 실제 서비스 화면은 Django가 서빙하는 `index.html`/`app.js`입니다.

---

## 🚀 로컬 실행

```bash
git clone https://github.com/cen04088/saju.git
cd saju
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env   # GEMINI_API_KEY, SECRET_KEY 등 입력

python manage.py migrate
python manage.py loaddata full_saju_data.json   # 사전 생성 콘텐츠 시딩(선택)
python manage.py collectstatic --no-input
python manage.py runserver
```

필요한 환경 변수 (`.env.example` 참고):

```ini
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_django_secret_key_here
```

> 앱인토스 웹뷰 밖에서 로컬 테스트 시 `X-Toss-User-Key`가 없으므로 `?toss_user_key=test123` 같은 쿼리 파라미터로 임시 식별자를 전달해야 합니다.

---

## ☁️ 배포

- **플랫폼:** Railway (Nixpacks 빌드 → `migrate` → `collectstatic` → `gunicorn`)
- **서비스 채널:** 앱인토스(App in Toss) 미니앱 "댕사주"

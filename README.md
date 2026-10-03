# 🐶 댕사주 (DaengSaju)

### "우리 댕댕이의 사주팔자가 궁금하다면?"

**앱인토스(App in Toss)**에서 서비스 중인, 반려견의 생년월일시로 사주팔자를 계산해 성격·오늘의 운세·주인과의 궁합을 알려주는 미니앱입니다.

사람의 사주가 아니라 **강아지의 사주**를 본다는 독특한 컨셉으로, 만세력(사주) 계산 로직에 반려동물 콘텐츠를 결합했습니다.

---

## ✨ 주요 기능

### 1. 댕사주 (반려견 사주 분석)
- 강아지 이름·생년월일(음력/윤달 지원)·태어난 시간(선택)·성별 입력
- 생일을 모르는 입양견은 **입양일·추정 생일** 기준으로도 볼 수 있음
- 년·월·일·시주 사주팔자 표 계산 (`sajupy` 만세력 라이브러리 기반, 음력은 양력으로 변환 후 계산)
- **일주(日柱) 캐릭터**: 60갑자마다 다른 별명·설명·키워드 + 띠
- 오행(목화토금수) 밸런스를 레이더 차트 + 막대그래프로 시각화
- 활력/에너지, 사회성, 간식운, 케어팁 4가지 카테고리의 성격 리포트 제공

### 2. 댕궁합 (반려견 ↔ 보호자 궁합)
- 보호자 생년월일시(음력 지원)를 입력하면 오행 상생·상극 관계(십성)로 궁합 점수·설명·관계 조언을 계산
- 띠 궁합(육합·삼합·충)으로 점수를 보정해 같은 오행 관계라도 결과가 달라짐

### 3. 댕친 궁합 (반려견 ↔ 친구 강아지)
- 친구 강아지 이름·생일만으로 두 아이의 케미 점수, 관계 설명, 함께 놀기 팁, 친구의 일주 캐릭터를 안내

### 4. 오늘의 산책운
- 그날의 **일진(日辰)** 과 강아지 오행의 관계로 매일 다른 산책 점수·메시지·행운의 색/방향을 안내

### 5. 재방문 & 출석
- 등록한 강아지는 메인에 바로가기 카드로 표시 → 탭 한 번으로 오늘 운세 확인
- 오늘 운세를 보면 출석 도장이 자동으로 찍힘. 이번 달 누적 1/3/5/7/10/15/20일에 부적 리워드, 월을 넘어 이어지는 연속 출석 표시

### 6. 결과 공유
- 토스 공유 링크(`intoss://daengsaju?share=토큰`)로 친구에게 **공개 사주 카드**를 보내고, 받은 사람은 카드 확인 후 바로 자기 강아지 사주로 유입
- 공개 카드에는 이름·오행·일주 캐릭터·띠만 노출 (생년월일·사주표는 비공개)

### 7. 앱인토스 사용자 연동
- `getAnonymousKey()`로 받은 사용자 키를 `X-Toss-User-Key` 헤더로 보내 사용자를 식별 (별도 로그인 불필요)
- 강아지 관련 API는 본인 키로 등록한 강아지만 조회 가능

---

## 🛠️ 기술 스택

| 영역 | 기술 |
|---|---|
| Backend | Python, Django 6, Django REST Framework |
| DB | SQLite(dev) / PostgreSQL(prod, `dj-database-url`) |
| 사주 계산 | `sajupy` (만세력·음력 변환), 커스텀 오행·십성·일주·띠 로직 |
| AI | Google Gemini (`gemini-2.5-flash`) — 콘텐츠 사전 생성용 |
| 프론트엔드 | 앱인토스 Granite(Vite) + Vanilla JS, SVG 레이더 차트, canvas-confetti(지연 로딩) |
| 배포 | Railway (Nixpacks + Gunicorn, Whitenoise), 앱인토스 콘솔(`ait deploy`) |
| 플랫폼 | 앱인토스(App in Toss) 미니앱 |

---

## 🧠 기술적으로 눈여겨볼 점 — LLM 콘텐츠 사전 생성 파이프라인

매 요청마다 LLM을 호출하면 응답 속도가 느리고 비용이 커집니다. 그래서 **"오행 × 십성 관계 × 버전"의 조합(예: 성격 유형 75종, 궁합 유형 50종, 일일 운세 75종)을 Gemini로 미리 생성해 DB에 저장**해두고, 실제 서비스에서는 캐시된 문구에 이름/조사(은·는, 이·가 등)만 자연스럽게 치환해 즉시 응답합니다.

여기에 규칙 기반 콘텐츠(일주 60종 캐릭터, 띠 궁합, 댕친 궁합)를 얹어 같은 오행끼리도 결과가 겹치지 않게 했습니다.

- `saju/services/manseryeok.py` — 만세력 계산(음력 변환 포함) + 오행/십성/일진 로직 + 한국어 조사 처리 유틸
- `saju/services/profiles.py` — 일주 캐릭터, 띠·띠 궁합, 댕친 궁합 문구
- `saju/services/gemini_ai.py` — Gemini 프롬프트 및 사전 생성 로직
- `saju/management/commands/pregenerate_*.py` — 사주/궁합/일일운세 아키타입을 배치로 채우는 관리 명령어

## ⚡ 저사양 기기 성능

헤드리스 Chrome에 CPU 6배 감속·GPU 끔(저가형 안드로이드 가정)을 걸고 시나리오별로 측정해 버벅임 원인을 찾아 고쳤습니다.

| 항목 | 개선 전 | 개선 후 |
|---|---|---|
| 메인 화면 대기 중 메인 스레드 사용 (3초당) | 857ms | 53ms |
| 결과 화면 진입 롱태스크 | 242ms | 87ms |
| 평생 사주 탭 전환 롱태스크 / 최대 멈춤 | 194ms / 183ms | 75ms / 100ms |
| 첫 화면 이미지 다운로드 | 1.9MB | 40KB |

- 별 배경을 `background-position` 대신 `transform` 애니메이션으로, 블롭의 `blur()` 필터를 방사형 그라데이션으로 바꿔 GPU 합성만 사용
- 스크롤 탭바·모달의 `backdrop-filter`, 상시 `will-change` 레이어 제거
- 레이더 차트를 Chart.js 대신 SVG로 직접 그림, 막대 그래프는 레이아웃 대신 `transform`으로 애니메이션
- 이미지를 표시 크기 WebP로 축소하고 숨은 화면의 이미지는 필요할 때 로드, 부적 저장은 원본 PNG 유지

---

## 📁 프로젝트 구조

```
saju/
├── config/                    # Django 프로젝트 설정
├── saju/                      # 메인 Django 앱 (API)
│   ├── models.py              # User, Dog, SajuBasics, Archetype*, Compatibility, Attendance 등
│   ├── views.py               # DRF APIView (사주/궁합/댕친/산책운/출석/공유 API)
│   ├── services/              # 만세력 계산, 규칙 기반 콘텐츠, Gemini 연동
│   └── management/commands/   # 사전 생성 배치 명령어
├── frontend/                  # 실제 서비스 화면 (앱인토스에 배포되는 Granite 번들)
│   ├── index.html
│   └── src/app.js, src/style.css
├── assets/                    # 공유 썸네일용 이미지 (/static/assets/ 로 공개)
└── full_saju_data.json / saju_data.json   # 사전 생성된 아키타입 콘텐츠 fixture
```

> Django 서버는 API와 공유 썸네일 이미지만 제공합니다. `/`는 헬스 체크 응답입니다.

### API 요약 (`/api/saju/`)

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `dogs/` | 강아지 등록 (같은 이름이면 정보 갱신) |
| GET | `me/dogs/` | 내 강아지 목록 (재방문 바로가기) |
| GET | `dogs/<id>/basics/` · `personality/` · `daily-luck/` | 원국 · 성격+일주 캐릭터 · 오늘의 산책운 |
| POST | `dogs/<id>/compatibility/` · `friend-compatibility/` | 보호자 궁합 · 댕친 궁합 |
| POST | `dogs/<id>/share/` | 공유 토큰 발급 |
| GET | `share/<token>/` | 공개 사주 카드 (인증 불필요) |
| GET/POST | `attendance/` | 출석 조회 / 도장 |

`share/<token>/`을 제외한 모든 API는 `X-Toss-User-Key` 헤더가 필요합니다.

---

## 🚀 로컬 실행

### 백엔드

```bash
git clone https://github.com/cen04088/saju.git
cd saju
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env   # GEMINI_API_KEY, SECRET_KEY 등 입력 (로컬은 DEBUG=True 추가)

python manage.py migrate
python manage.py loaddata full_saju_data.json   # 사전 생성 콘텐츠 시딩
python manage.py runserver 127.0.0.1:8010
python manage.py test saju                      # 테스트
```

### 프론트엔드

```bash
cd frontend
npm install
# 로컬 백엔드에 붙이기 (미지정 시 운영 API 사용)
set VITE_API_BASE_URL=http://127.0.0.1:8010
npx vite --port 5181
```

> 토스 웹뷰 밖에서는 `getAnonymousKey()`를 쓸 수 없어서, 개발 모드에서는 브라우저별 임시 사용자 키를 자동으로 만듭니다. 여러 사용자를 흉내 내려면 `?devUserKey=아무값`을 붙이세요. 공유 카드는 `?share=토큰`으로 확인할 수 있습니다.

### 환경 변수

| 이름 | 설명 |
|---|---|
| `SECRET_KEY` | Django 시크릿 키 (운영 필수) |
| `DEBUG` | `True`면 개발 모드 |
| `GEMINI_API_KEY` | 콘텐츠 사전 생성용 |
| `DATABASE_URL` | 운영 PostgreSQL |
| `ALLOWED_HOSTS` | 쉼표 구분 (기본 `*`) |
| `CORS_EXTRA_ORIGINS` | 토스 미니앱 도메인 외에 허용할 출처 (쉼표 구분) |
| `CORS_ALLOW_ALL_ORIGINS` | 비상용. `True`면 모든 출처 허용 (기본 꺼짐) |

---

## ☁️ 배포

- **API:** Railway (Nixpacks 빌드 → `migrate` → `collectstatic` → `gunicorn`)
- **화면:** `frontend/`에서 `npm run build && npm run deploy` (앱인토스 콘솔 API 키 필요)
- **서비스 채널:** 앱인토스(App in Toss) 미니앱 "댕사주"

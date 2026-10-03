# 새 일러스트 제작 가이드

기존 그림체(오행 강아지 5종·출석 부적 7종)에 맞춰 새 일러스트를 만들 때 쓰는 프롬프트와,
만든 원본을 앱 규격으로 바꾸는 방법을 정리한다.

## 공통 규칙

- 이미지 안에 글자·숫자·로고를 넣지 않는다. 문구는 화면에서 텍스트로 쓴다.
- 토스 로고, 토스 블루(#0064FF 계열), 토스 화면을 닮은 구성은 쓰지 않는다.
- 원본은 PNG로 받는다. 정사각형 그림은 1024×1024, 부적은 1:2 세로(887×1774 이상)로 받는다.
- 종횡비가 다른 원본은 늘리지 않는다. 잘라서 쓸지는 직접 보고 정한다(`--crop`).

## 그림체 A — 오행 강아지 스타일 (정사각형)

기존 `*_dog.webp`와 같은 스타일이다. 흰 배경 위에 한 가지 색 계열만 쓴 플랫 벡터 스티커 느낌으로 만든다.

```
Flat vector illustration, cute fluffy puppy, {장면}, limited palette of {색 계열} shades only,
stylized swirls, small sparkles and dots floating around, clean pure white background,
soft oval shadow under the puppy, sticker-like, smooth shapes, no outlines, no text, no logo,
centered composition, square 1:1
```

### 세트 1. 12지 띠 강아지 (12종) — `zodiac_<지지>.png`

일주 캐릭터 카드의 띠 배지 옆이나 공유 카드에 띠별 그림으로 쓴다. 색은 앱의 보라·금색에 맞춰
`lavender, violet and warm gold`로 통일한다.

| 파일 | 띠 | {장면} |
|---|---|---|
| zodiac_ja | 쥐 | wearing a soft gray mouse-ear hood, holding a tiny grain of rice |
| zodiac_chuk | 소 | wearing a cow-pattern hood with two small horns, sitting calmly |
| zodiac_in | 호랑이 | wearing a tiger-striped hood, playful pounce pose |
| zodiac_myo | 토끼 | wearing long bunny ears, hopping |
| zodiac_jin | 용 | with small dragon horns and a flowing mane, riding a little cloud |
| zodiac_sa | 뱀 | with a scaly scarf gently coiled around the neck |
| zodiac_o | 말 | with a horse mane hood, galloping pose |
| zodiac_mi | 양 | wearing a fluffy sheep-wool hood with curled horns |
| zodiac_sin | 원숭이 | wearing monkey ears, holding a banana |
| zodiac_yu | 닭 | wearing a rooster-comb hat, proud chest-out pose |
| zodiac_sul | 개 | proud puppy with a golden bell collar, wagging tail |
| zodiac_hae | 돼지 | wearing a piglet hood with a round snout, happy smile |

### 세트 2. 상태 일러스트 (3종) — `state_<이름>.png`

| 파일 | 쓰는 곳 | {장면} / {색 계열} |
|---|---|---|
| state_loading | 분석 중 화면 | wearing a tiny astrologer hat, gazing into a glowing crystal ball with stars / violet |
| state_error | 서버 오류 안내 | happily munching a bone-shaped treat with crumbs around / warm orange |
| state_welcome | 첫 방문·강아지 등록 전 | holding an empty heart-shaped name tag in its mouth / soft pink |

## 그림체 B — 출석 부적 스타일 (세로 1:2)

기존 `talisman_*.webp`와 같은 스타일이다. 남색 밤하늘 배경에 금박 장식을 쓴다.

```
Ornate vertical talisman card, 1:2 portrait ratio, deep midnight navy background with
constellations and stars, intricate glowing gold filigree frame with an arched top,
Korean traditional knot ornaments (maedeup) with tassels at the top and bottom,
gold cloud patterns, {가운데 장면}, highly detailed, luxurious gold and navy only,
no text, no logo
```

### 세트 3. 추가 부적 (선택)

지금 부적은 이번 달 1·3·5·7·10·15·20번째 출석에 준다(`MILESTONES`, 백엔드 `AttendanceView.MILESTONES`).
아래 부적을 쓰려면 프론트와 백엔드의 마일스톤을 함께 늘려야 한다.

| 파일 | 조건(예시) | {가운데 장면} |
|---|---|---|
| talisman_25 | 이번 달 25번째 출석 | a silver-furred puppy sitting under a full moon, holding a jade bead |
| talisman_28 | 이번 달 28번째 출석(어느 달이든 가능한 최대치) | a regal puppy wearing a crown, sitting on a lotus throne, rainbow aura |

## 앱 규격으로 바꾸기

원본 PNG를 받으면 아래 명령으로 `frontend/public/assets/`에 표시용 WebP를 만든다.
Pillow가 필요하다(`pip install pillow`).

```bash
python scripts/illustrations/optimize.py zodiac 원본/zodiac_ja.png 원본/zodiac_chuk.png
python scripts/illustrations/optimize.py state 원본/state_error.png
python scripts/illustrations/optimize.py talisman 원본/talisman_25.png
```

| 종류 | 표시용 WebP | 함께 두는 것 |
|---|---|---|
| dog · zodiac · state | 480×480 | 없음 |
| talisman | 440×880 | 887×1774 PNG (부적 저장하기용 원본) |

결과 파일 이름은 원본 이름을 따른다(`zodiac_ja.png` → `zodiac_ja.webp`).
화면에 연결하는 코드는 그림이 준비된 뒤에 추가한다(없는 그림을 참조하면 빈 이미지가 보인다).

import {
  getAnonymousKey,
  getSchemeUri,
  getTossShareLink,
  loadFullScreenAd,
  saveBase64Data,
  share,
  showFullScreenAd,
  TossAds,
} from '@apps-in-toss/web-framework';
import { DOG_BREEDS, dogBreedImage } from './dog-breeds.js';

// 로컬 개발 시 VITE_API_BASE_URL 로 로컬 백엔드를 가리킬 수 있음
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'https://web-production-285b5.up.railway.app').replace(/\/+$/, '');
const APP_SCHEME = 'intoss://daengsaju';
const USER_KEY_TIMEOUT_MS = 4000;
const DEV_USER_KEY_STORAGE = 'daengsaju_dev_user_key';
// 테스트 광고 ID는 로컬 개발 서버에서만. 앱인토스 검수도 QR 테스트와 같은 도메인에서 열리므로
// 배포 번들에는 항상 실제 광고가 나와야 함(테스트 광고는 반려 사유). 테스트 광고 번들이 필요하면 VITE_USE_TEST_ADS=true 로 빌드
const USE_TEST_ADS = import.meta.env.DEV || import.meta.env.VITE_USE_TEST_ADS === 'true';
const BANNER_AD_ID = USE_TEST_ADS ? 'ait-ad-test-banner-id' : 'ait.v2.live.82786c3925d743b3';
const FULLSCREEN_AD_ID = USE_TEST_ADS ? 'ait-ad-test-interstitial-id' : 'ait.v2.live.3c235f3d3a424553'; // 전면형
const DEFAULT_ERROR_MESSAGE = '잠시 후 다시 시도해 주세요.';

const ELEMENTS = {
  '목': { slug: 'wood', hanja: '木', className: 'text-wood' },
  '화': { slug: 'fire', hanja: '火', className: 'text-fire' },
  '토': { slug: 'earth', hanja: '土', className: 'text-earth' },
  '금': { slug: 'metal', hanja: '金', className: 'text-metal' },
  '수': { slug: 'water', hanja: '水', className: 'text-water' },
};
const DEFAULT_ELEMENT = '화';

const MODE_COPY = {
  general: { title: '우리 강아지 정보', submit: '오늘 운세 뽑기', share: '사주 카드 공유하기', portrait: 'hanji-dog' },
  chemistry: { title: '보호자 궁합', submit: '궁합 보기', share: '궁합 결과 공유하기', portrait: 'guardian' },
  friend: { title: '친구 강아지 궁합', submit: '궁합 보기', share: '댕친 궁합 공유하기', portrait: 'friends' },
};

const DAILY_MISSIONS = [
  '산책하다 좋아하는 냄새를 만나면, 잠깐 멈춰 기다려 주세요.',
  '평소 좋아하는 장난감을 골라 같이 놀아 주세요.',
  '오늘 가장 웃겼던 강아지 표정을 사진으로 남겨 보세요.',
  '산책이 끝나면 좋아하는 자리에 함께 앉아 쉬어 보세요.',
  '좋아하는 장난감을 눈에 잘 띄는 곳에 숨기고 같이 찾아보세요.',
  '오늘은 산책을 마치고 이름을 불러 다정하게 인사해 주세요.',
  '편안히 쉬고 있다면 옆에 앉아 느긋한 시간을 보내 보세요.',
];

// 출석 부적: 이번 달 누적 출석 일수 기준
const MILESTONES = [1, 3, 5, 7, 10, 15, 20];
const TALISMAN_REWARDS = {
  1: { name: '시작의 코기 부적', desc: '첫 출석 완료! 오늘의 시작마다 산뜻한 행운이 따라붙을 거예요.' },
  3: { name: '초심자의 뼈다귀 부적', desc: '이번 달 3번째 출석! 멍멍이 에너지가 솟아나요.' },
  5: { name: '복슬복슬 말티즈 부적', desc: '이번 달 5번째 출석! 포근한 기운이 차곡차곡 쌓이고 있어요.' },
  7: { name: '행운의 댕댕 부적', desc: '럭키 7번째 출석! 기분 좋은 일이 가득할 거예요.' },
  10: { name: '재물운 명탐정 부적', desc: '이번 달 10번째 출석! 생각지 못한 간식이나 행운이 찾아올 거예요.' },
  15: { name: '대박 황금 부적', desc: '이번 달 15번째 출석! 주변에서 많은 복이 찾아오는 시기예요.' },
  20: { name: '전설의 댕댕 부적', desc: '이번 달 20번째 출석! 진정한 댕사주 마스터예요!' },
};

// ─── 공용 유틸 ───────────────────────────────────────────────────────────
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}

// 서버 문구에는 사용자가 입력한 이름이 섞여 있으므로 반드시 이스케이프 후 강조/줄바꿈만 허용
function formatText(text) {
  if (!text) return '';
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<span class="highlight-text">$1</span>')
    .replace(/\n/g, '<br>');
}

function formatLetterParagraphs(text) {
  return (text || '').trim()
    .split(/\r?\n\s*\r?\n/)
    .filter(Boolean)
    .map((paragraph) => `<p>${formatText(paragraph)}</p>`)
    .join('');
}

function hasBatchim(name) {
  if (!name) return false;
  const code = name.charCodeAt(name.length - 1);
  if (code < 0xAC00 || code > 0xD7A3) return false;
  return (code - 0xAC00) % 28 > 0;
}

function withJosa(name, josa) {
  const [withBatchim, withoutBatchim] = {
    '은/는': ['은', '는'],
    '이/가': ['이', '가'],
    '을/를': ['을', '를'],
    '와/과': ['과', '와'],
  }[josa];
  return name + (hasBatchim(name) ? withBatchim : withoutBatchim);
}

// 보호자 궁합 관계(십성)를 쉬운 말로: 명리 용어만 보여주면 뜻을 알기 어려움
const RELATION_PLAIN_LABELS = { 비겁: '닮은꼴형', 인성: '보살핌형', 식상: '활력형', 재성: '변화형', 관성: '리더형' };

function relationPlainLabel(relationshipType) {
  return RELATION_PLAIN_LABELS[String(relationshipType || '').slice(0, 2)] || '궁합';
}

function renderCompatibilityRelation(chip, relationshipType) {
  const plainLabel = document.createElement('strong');
  plainLabel.textContent = relationPlainLabel(relationshipType);
  const termLabel = document.createElement('small');
  termLabel.textContent = relationshipType;
  chip.replaceChildren(plainLabel, termLabel);
}

function elementInfo(element) {
  return ELEMENTS[element] || ELEMENTS[DEFAULT_ELEMENT];
}

function elementLabel(element) {
  const info = ELEMENTS[element];
  return info ? `${element}(${info.hanja})` : (element || '-');
}

function setMinhwaPortrait(img, breed, element) {
  img.parentElement.dataset.element = ELEMENTS[element]?.slug || '';
  img.src = dogBreedImage(breed);
}

// ─── 아이콘 (public/assets/icons/sprite.svg) ─────────────────────────────
const SVG_NS = 'http://www.w3.org/2000/svg';
const ICON_SPRITE = './assets/icons/sprite.svg';

function svgIcon(id, className) {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', className);
  svg.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS(SVG_NS, 'use');
  use.setAttribute('href', `${ICON_SPRITE}#${id}`);
  svg.append(use);
  return svg;
}

// 오행 아이콘: 색은 .text-wood 등 오행 글자색을 그대로 따름
function elementIcon(element) {
  const info = elementInfo(element);
  return svgIcon(`el-${info.slug}`, `el-icon ${info.className}`);
}

// "화(火)" 같은 오행 이름 앞에 아이콘을 붙여 채움
function setElementLabel(target, element) {
  if (ELEMENTS[element]) {
    target.replaceChildren(elementIcon(element), elementLabel(element));
  } else {
    target.textContent = elementLabel(element);
  }
}

const ZODIAC_HANJA = {
  자: '子', 축: '丑', 인: '寅', 묘: '卯', 진: '辰', 사: '巳', 오: '午', 미: '未', 신: '申', 유: '酉', 술: '戌', 해: '亥',
};

// 띠 도장: 붉은 인장 위에 지지 한자 (예: 해 → 亥)
function zodiacSeal(branch) {
  const hanja = ZODIAC_HANJA[branch];
  if (!hanja) return null;
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', 'zodiac-seal');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  svg.innerHTML = '<rect x="1" y="1" width="22" height="22" rx="6" fill="#E5533D"/>'
    + '<rect x="3.2" y="3.2" width="17.6" height="17.6" rx="4.2" fill="none" stroke="#FFE4DC" stroke-opacity=".65" stroke-width="1"/>'
    + `<text x="12" y="16.4" text-anchor="middle" font-size="12.5" font-weight="700" fill="#FFF7ED">${hanja}</text>`;
  return svg;
}

// 연속 출석 메달: 7·14·30일마다 색이 바뀜 (동 → 은 → 금 → 보라)
function streakMedal(days) {
  const tier = days >= 30 ? 4 : days >= 14 ? 3 : days >= 7 ? 2 : 1;
  return svgIcon('streak', `streak-medal streak-tier-${tier}`);
}

const SEOUL_DATE = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul', dateStyle: 'short' });
const KOREAN_DATE = new Intl.DateTimeFormat('ko-KR', {
  timeZone: 'Asia/Seoul', month: 'long', day: 'numeric', weekday: 'long',
});

function todayIso() {
  return SEOUL_DATE.format(new Date());
}

function fortuneDate(date) {
  return KOREAN_DATE.format(new Date(`${date}T00:00:00+09:00`));
}

function withTimeout(promise, ms) {
  return Promise.race([promise, new Promise((resolve) => setTimeout(() => resolve(undefined), ms))]);
}

// 폭죽 효과는 처음 필요할 때만 불러와 첫 화면 로딩을 가볍게 유지
let confettiPromise = null;
function loadConfetti() {
  confettiPromise ??= import('canvas-confetti').then((module) => module.default);
  return confettiPromise;
}

// ─── 사용자 키 & API ─────────────────────────────────────────────────────
function getDevUserKey() {
  const fromQuery = new URLSearchParams(window.location.search).get('devUserKey');
  try {
    const key = fromQuery || localStorage.getItem(DEV_USER_KEY_STORAGE) || `dev-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(DEV_USER_KEY_STORAGE, key);
    return key;
  } catch {
    return fromQuery || 'dev-user';
  }
}

async function resolveUserKey() {
  try {
    const result = await withTimeout(getAnonymousKey(), USER_KEY_TIMEOUT_MS);
    if (result && result !== 'ERROR' && result.type === 'HASH' && result.hash) {
      return result.hash;
    }
  } catch (error) {
    console.warn('[UserKey] Toss bridge unavailable', error);
  }
  // 토스 밖(로컬 개발)에서는 브라우저별 임시 키로 대신 테스트
  return import.meta.env.DEV ? getDevUserKey() : '';
}

let userKey = '';
const userKeyReady = resolveUserKey().then((key) => {
  userKey = typeof key === 'string' ? key.trim() : '';
  return userKey;
});

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function api(path, { method = 'GET', body } = {}) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (userKey) headers['X-Toss-User-Key'] = userKey;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('', 0);
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    throw new ApiError((data && (data.error || data.detail)) || '', response.status);
  }
  return data;
}

function apiErrorMessage(error) {
  if (!(error instanceof ApiError)) return '';
  if (error.status === 0) return '인터넷 연결을 확인한 뒤\n다시 시도해주세요.';
  if (error.status === 403) return '토스 사용자 정보를 확인할 수 없어요.\n토스 앱에서 댕사주를 다시 열어주세요.';
  if (error.status >= 500) return '';
  return error.message;
}

function readShareToken() {
  let token = '';
  try {
    const schemeUri = getSchemeUri();
    if (schemeUri) token = new URL(schemeUri).searchParams.get('share') || '';
  } catch {
    token = '';
  }
  token ||= new URLSearchParams(window.location.search).get('share') || '';
  return /^[A-Za-z0-9_-]{8,64}$/.test(token) ? token : '';
}

// ─── 화면 ────────────────────────────────────────────────────────────────
function init() {
  const $ = (id) => document.getElementById(id);

  const screens = {
    main: $('main-screen'),
    input: $('input-screen'),
    loading: $('loading-screen'),
    result: $('result-screen'),
    share: $('share-screen'),
  };

  const btnSubmit = $('btn-submit');
  const btnShare = $('btn-share');
  const chemistrySection = $('chemistry-result-section');
  const friendSection = $('friend-result-section');
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  const state = {
    mode: 'general', // 'general' | 'chemistry' | 'friend'
    myDogs: [],
    selectedDogId: null, // 강아지 id 또는 'new'(새 아이 입력)
    prefilledDogId: null,
    currentDog: null,
    lastChemistry: null,
    lastFriend: null,
    attendance: null,
    attendanceDate: null,
    dailyLuck: null,
    lifetime: null,
    firstResultTab: 'tab-today',
    submitting: false,
    sharing: false,
  };

  // ─── 토스트 & 에러 ───
  let toastTimer = null;
  function showToast(message, duration = 2600) {
    const toast = $('toast');
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), duration);
  }

  function showErrorModal(message) {
    $('error-message').textContent = message || DEFAULT_ERROR_MESSAGE;
    $('error-modal').style.display = 'flex';
  }

  function showApiError(error) {
    showErrorModal(apiErrorMessage(error));
  }

  async function requireUserKey() {
    const key = await userKeyReady;
    if (key) return key;
    showErrorModal('토스 사용자 정보를 확인할 수 없어요.\n토스 앱에서 댕사주를 다시 열어주세요.');
    return '';
  }

  $('btn-close-error').addEventListener('click', () => {
    $('error-modal').style.display = 'none';
  });

  // ─── 탭 ───
  function updateShareButton() {
    const isDaily = state.mode === 'general' && $('tab-today').classList.contains('active');
    btnShare.textContent = state.sharing ? '공유 링크 만드는 중…'
      : isDaily ? '오늘 운세 공유하기' : MODE_COPY[state.mode].share;
    btnShare.disabled = state.sharing || (state.mode === 'general' && !isDaily && !state.lifetime?.loaded);
  }

  function activateTab(tabId) {
    screens.result.classList.toggle('daily-view', tabId === 'tab-today');
    tabBtns.forEach((b) => {
      const selected = b.dataset.tab === tabId;
      b.classList.toggle('active', selected);
      b.setAttribute('aria-pressed', String(selected));
    });
    tabContents.forEach((c) => c.classList.toggle('active', c.id === tabId));

    const scrollContainer = document.querySelector('.result-scroll');
    if (scrollContainer) scrollContainer.scrollTop = 0;

    revealCards();
    if (state.mode === 'general') {
      updateShareButton();
      if (tabId === 'tab-lifetime') {
        if (state.lifetime?.loaded) animateBars();
        else loadLifetime();
      }
    }
  }

  tabBtns.forEach((btn) => {
    btn.addEventListener('click', () => activateTab(btn.dataset.tab));
  });

  function revealCards() {
    const cards = document.querySelectorAll('.tab-content.active .fade-in');
    cards.forEach((card) => card.classList.add('reveal'));
  }

  // ─── 네비게이션 ───
  // 메인은 해시 없이 두어야 토스 네이티브 뒤로가기가 앱 종료 확인을 띄움
  window.addEventListener('popstate', () => {
    const hash = window.location.hash.replace('#', '') || 'main-screen';
    showScreen(Object.values(screens).find((screen) => screen.id === hash) || screens.main);
  });

  function navigateTo(screenElement, pushHistory = true) {
    showScreen(screenElement);

    if (pushHistory) {
      const targetHash = screenElement.id === 'main-screen' ? '' : `#${screenElement.id}`;
      // pushState를 써서 앵커로 자동 스크롤되지 않게 함
      if (window.location.hash !== targetHash && (window.location.hash || targetHash !== '')) {
        history.pushState(null, '', targetHash || window.location.pathname + window.location.search);
      }
    }
  }

  let activeScreen = null;
  function showScreen(screenElement) {
    activeScreen = screenElement;
    Object.values(screens).forEach((screen) => screen.classList.toggle('active', screen === screenElement));
    if (screenElement === screens.main) {
      renderTodayBadge();
      mountTossBanner();
    } else {
      unmountTossBanner();
    }
  }

  // 새 결과를 띄우기 직전에 모드별 레이아웃을 맞춤
  function prepareResultScreen(firstTab = 'tab-today') {
    const isGeneral = state.mode === 'general';
    const tabNav = document.querySelector('.tab-nav');
    if (tabNav) tabNav.style.display = isGeneral ? 'flex' : 'none';
    $('tab-today').style.display = isGeneral ? '' : 'none';
    $('tab-lifetime').style.display = isGeneral ? '' : 'none';
    chemistrySection.style.display = state.mode === 'chemistry' ? 'block' : 'none';
    friendSection.style.display = state.mode === 'friend' ? 'block' : 'none';
    screens.result.classList.toggle('fortune-result', isGeneral);
    if (!isGeneral) screens.result.classList.remove('daily-view');
    updateShareButton();

    lockChemReport();
    if (isGeneral) {
      activateTab(firstTab);
    } else {
      const scrollContainer = document.querySelector('.result-scroll');
      if (scrollContainer) scrollContainer.scrollTop = 0;
    }
  }

  function setDogNameDisplays(name) {
    document.querySelectorAll('.dog-name-display').forEach((el) => {
      el.textContent = name;
    });
  }

  // ─── 토스 배너 광고 ───
  let isTossAdsReady = false;
  let tossBannerInstance = null;

  function mountTossBanner() {
    if (!isTossAdsReady) return;
    const adContainer = $('toss-ad-container');
    if (!adContainer) return;

    if (tossBannerInstance) {
      tossBannerInstance.destroy();
      tossBannerInstance = null;
    }
    tossBannerInstance = TossAds.attachBanner(BANNER_AD_ID, adContainer, {
      variant: 'card',
      theme: 'light',
      callbacks: {
        onAdFailedToRender: (p) => console.error('[Banner] failed', p),
        onNoFill: (p) => console.warn('[Banner] no fill', p),
      },
    });
  }

  function unmountTossBanner() {
    if (tossBannerInstance) {
      tossBannerInstance.destroy();
      tossBannerInstance = null;
    }
  }

  let bannerSupported = false;
  try {
    bannerSupported = TossAds && typeof TossAds.initialize === 'function'
      ? (typeof TossAds.initialize.isSupported === 'function' ? TossAds.initialize.isSupported() : true)
      : false;
  } catch (error) {
    console.warn('[TossAds] isSupported check failed', error);
  }

  if (bannerSupported) {
    TossAds.initialize({
      callbacks: {
        onInitialized: () => {
          isTossAdsReady = true;
          if (screens.main.classList.contains('active')) mountTossBanner();
        },
        onInitializationFailed: (err) => console.error('[TossAds] init failed', err),
      },
    });
  }

  // ─── 전면형 광고 (궁합 상세 풀이 잠금 해제) ───
  // 광고가 닫히면 풀이를 연다. 광고를 쓸 수 없는 환경(토스 밖·미지원 버전·광고 없음)이면 사용자를 막지 않고 그냥 연다.
  const AD_LOAD_STALE_MS = 15000;
  const fullScreenAd = { loaded: false, loadingSince: 0, unregister: null, waiters: [] };

  function isFullScreenAdSupported() {
    // isSupported()는 토스 웹뷰에서만 동작 - try-catch 필수
    try {
      return typeof loadFullScreenAd.isSupported !== 'function' || loadFullScreenAd.isSupported();
    } catch {
      return false; // 웹뷰 외부(일반 브라우저) 환경
    }
  }

  function settleAdWaiters(ready) {
    fullScreenAd.waiters.splice(0).forEach((resolve) => resolve(ready));
  }

  function preloadFullScreenAd() {
    if (fullScreenAd.loaded || !isFullScreenAdSupported()) return;
    // 로드 이벤트가 유실돼도(배너와 동시 로드 등) 다음 시도에서 다시 불러오도록 오래된 로드는 버림
    if (fullScreenAd.loadingSince && Date.now() - fullScreenAd.loadingSince < AD_LOAD_STALE_MS) return;

    if (fullScreenAd.unregister) fullScreenAd.unregister();
    fullScreenAd.loadingSince = Date.now();
    const onFailed = (err) => {
      console.error('[FullScreenAd] load error:', err);
      fullScreenAd.loadingSince = 0;
      settleAdWaiters(false);
    };
    try {
      fullScreenAd.unregister = loadFullScreenAd({
        options: { adGroupId: FULLSCREEN_AD_ID },
        onEvent: (event) => {
          if (event.type !== 'loaded') return;
          fullScreenAd.loaded = true;
          fullScreenAd.loadingSince = 0;
          settleAdWaiters(true);
        },
        onError: onFailed,
      });
    } catch (err) {
      onFailed(err);
    }
  }

  /** 광고가 준비되면 true, 시간 안에 못 불러오면 false */
  function waitForFullScreenAd(timeoutMs) {
    preloadFullScreenAd();
    if (fullScreenAd.loaded) return Promise.resolve(true);
    if (!fullScreenAd.loadingSince) return Promise.resolve(false);
    return new Promise((resolve) => {
      fullScreenAd.waiters.push(resolve);
      setTimeout(() => resolve(false), timeoutMs);
    });
  }

  /** 전면형 광고를 보여주고, 광고가 닫히거나 띄우지 못하면 끝남 */
  function showFullScreenAdOnce() {
    return new Promise((resolve) => {
      let settled = false;
      let unregisterShow = null;
      let timer = null;
      const finish = () => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        if (typeof unregisterShow === 'function') unregisterShow();
        preloadFullScreenAd(); // load→show→load 순환
        resolve();
      };
      // 이벤트가 오지 않으면 버튼이 '불러오는 중'에 갇히지 않게: 시작 신호 10초, 광고 표시 중 3분
      const armTimer = (ms) => {
        clearTimeout(timer);
        timer = setTimeout(finish, ms);
      };

      fullScreenAd.loaded = false; // 한 번 보여준 광고는 다시 쓰지 않음
      armTimer(10000);
      try {
        unregisterShow = showFullScreenAd({
          options: { adGroupId: FULLSCREEN_AD_ID },
          onEvent: (event) => {
            if (event.type === 'dismissed' || event.type === 'failedToShow') finish();
            else armTimer(180000);
          },
          onError: (err) => {
            console.error('[FullScreenAd] show error:', err);
            finish();
          },
        });
      } catch (err) {
        console.error('[FullScreenAd] show error:', err);
        finish();
      }
    });
  }

  function lockChemReport() {
    $('locked-chem-container').classList.add('is-locked');
    $('locked-chem-content').inert = true;
  }

  function unlockChemReport() {
    $('locked-chem-container').classList.remove('is-locked');
    $('locked-chem-content').inert = false;
  }

  const btnUnlockChem = $('btn-unlock-chem');
  const unlockButtonHtml = btnUnlockChem.innerHTML;
  btnUnlockChem.addEventListener('click', async () => {
    if (btnUnlockChem.classList.contains('is-loading')) return;
    btnUnlockChem.classList.add('is-loading');
    btnUnlockChem.textContent = '⏳ 광고 불러오는 중...';

    try {
      if (await waitForFullScreenAd(8000)) await showFullScreenAdOnce();
      unlockChemReport();
    } finally {
      btnUnlockChem.classList.remove('is-loading');
      btnUnlockChem.innerHTML = unlockButtonHtml;
    }
  });

  // ─── 입력 폼 ───
  const form = {
    dogName: $('dog-name'),
    dogBreed: $('dog-breed'),
    dogDate: $('dog-date'),
    dogDateLabel: $('dog-date-label'),
    dogTime: $('dog-time'),
    birthOptions: $('dog-birth-options'),
    dogLunar: $('dog-lunar'),
    dogLeap: $('dog-leap'),
    dogEstimated: $('dog-estimated'),
    ownerSection: $('owner-input-section'),
    ownerDate: $('owner-date'),
    ownerTime: $('owner-time'),
    ownerLunar: $('owner-lunar'),
    ownerLeap: $('owner-leap'),
    friendSection: $('friend-input-section'),
    friendName: $('friend-name'),
    friendDate: $('friend-date'),
    friendLunar: $('friend-lunar'),
    friendLeap: $('friend-leap'),
  };

  form.dogBreed.replaceChildren(
    new Option('선택 안 함', ''),
    new Option('믹스견', 'mixed'),
    ...DOG_BREEDS.map(({ id, label }) => new Option(label, id)),
  );

  [form.dogDate, form.ownerDate, form.friendDate].forEach((input) => {
    input.max = todayIso();
  });

  // 윤달은 음력일 때만 선택 가능
  function bindLeapToggle(lunarInput, leapInput) {
    const sync = () => {
      leapInput.disabled = !lunarInput.checked || lunarInput.disabled;
      if (leapInput.disabled) leapInput.checked = false;
    };
    lunarInput.addEventListener('change', sync);
    sync();
    return sync;
  }
  const syncDogLeap = bindLeapToggle(form.dogLunar, form.dogLeap);
  bindLeapToggle(form.ownerLunar, form.ownerLeap);
  bindLeapToggle(form.friendLunar, form.friendLeap);

  // 생일을 모르는 아이(입양견 등)는 입양일·추정일 기준으로, 시간·음력 입력은 숨김
  function syncEstimated() {
    const estimated = form.dogEstimated.checked;
    form.dogDateLabel.textContent = estimated ? '입양일 또는 추정 생일' : '강아지 생일';
    form.birthOptions.classList.toggle('hidden', estimated);
    form.dogLunar.disabled = estimated;
    if (estimated) {
      form.dogLunar.checked = false;
      form.dogTime.value = '';
    }
    syncDogLeap();
  }
  form.dogEstimated.addEventListener('change', syncEstimated);

  function readDogForm() {
    const estimated = form.dogEstimated.checked;
    const lunar = !estimated && form.dogLunar.checked;
    const gender = document.querySelector('input[name="dog-gender"]:checked')?.value;
    return {
      name: form.dogName.value.trim(),
      breed: form.dogBreed.value,
      birth_date: form.dogDate.value,
      birth_time: estimated ? null : (form.dogTime.value || null),
      is_lunar: lunar,
      is_leap_month: lunar && form.dogLeap.checked,
      gender: gender || 'MALE',
      is_estimated_birth: estimated,
    };
  }

  function fillDogForm(dog) {
    form.dogName.value = dog?.name || '';
    form.dogBreed.value = dog?.breed || '';
    form.dogDate.value = dog?.birth_date || '';
    form.dogTime.value = dog?.birth_time ? dog.birth_time.slice(0, 5) : '';
    form.dogEstimated.checked = Boolean(dog?.is_estimated_birth);
    form.dogLunar.checked = Boolean(dog?.is_lunar);
    syncEstimated();
    form.dogLeap.checked = Boolean(dog?.is_leap_month) && form.dogLunar.checked;
    form.birthOptions.open = Boolean(dog?.birth_time || dog?.is_lunar);
    const neutered = dog?.gender === 'NEUTERED';
    $('dog-neutered').disabled = !neutered;
    $('dog-neutered').classList.toggle('hidden', !neutered);
    $('dog-neutered-label').classList.toggle('hidden', !neutered);
    const genderId = { MALE: 'dog-m', FEMALE: 'dog-f', NEUTERED: 'dog-neutered' };
    $(genderId[dog?.gender] || 'dog-m').checked = true;
  }

  function getSelectedDog() {
    return state.myDogs.find((dog) => dog.id === state.selectedDogId) || null;
  }

  // 등록한 아이가 있으면 폼을 미리 채워 다시 입력하지 않게 함
  function prepareDogForm() {
    const dog = getSelectedDog();
    if (dog) {
      fillDogForm(dog);
      state.prefilledDogId = dog.id;
    } else if (state.prefilledDogId !== null) {
      fillDogForm(null);
      state.prefilledDogId = null;
    }
  }

  function openInput(mode, firstTab = 'tab-today') {
    state.mode = mode;
    state.firstResultTab = firstTab;
    $('input-title').textContent = MODE_COPY[mode].title;
    const portrait = firstTab === 'tab-lifetime' ? 'lifetime' : MODE_COPY[mode].portrait;
    $('input-portrait').src = `./assets/minhwa/${portrait}.webp`;
    btnSubmit.textContent = firstTab === 'tab-lifetime' ? '평생 사주 보기' : MODE_COPY[mode].submit;
    form.ownerSection.classList.toggle('hidden', mode !== 'chemistry');
    form.friendSection.classList.toggle('hidden', mode !== 'friend');
    clearDogFormError();
    prepareDogForm();
    navigateTo(screens.input);
  }

  function clearDogFormError() {
    [form.dogName, form.dogDate].forEach((field) => {
      $(`${field.id}-error`).classList.add('hidden');
      field.removeAttribute('aria-invalid');
    });
  }

  $('btn-input-back').addEventListener('click', () => history.back());
  $('btn-edit-dog').addEventListener('click', () => openInput('general'));
  [form.dogName, form.dogDate].forEach((field) => field.addEventListener('input', clearDogFormError));
  form.dogEstimated.addEventListener('change', clearDogFormError);

  $('btn-lifetime').addEventListener('click', () => openMyFortune('tab-lifetime'));
  $('btn-chemistry').addEventListener('click', () => openInput('chemistry'));
  $('btn-friend').addEventListener('click', () => openInput('friend'));
  $('btn-share-cta').addEventListener('click', () => openMyFortune());

  function buildModeRequest() {
    if (state.mode === 'chemistry') {
      if (!form.ownerDate.value) return { error: '보호자 생년월일을 입력해주세요!' };
      const lunar = form.ownerLunar.checked;
      return {
        path: 'compatibility',
        body: {
          owner_birth_date: form.ownerDate.value,
          owner_birth_time: form.ownerTime.value || null,
          owner_is_lunar: lunar,
          owner_is_leap_month: lunar && form.ownerLeap.checked,
        },
      };
    }
    if (state.mode === 'friend') {
      const friendName = form.friendName.value.trim();
      if (!friendName || !form.friendDate.value) return { error: '친구 강아지 이름과 생년월일을 입력해주세요!' };
      const lunar = form.friendLunar.checked;
      return {
        path: 'friend-compatibility',
        body: {
          friend_name: friendName,
          friend_birth_date: form.friendDate.value,
          friend_is_lunar: lunar,
          friend_is_leap_month: lunar && form.friendLeap.checked,
        },
      };
    }
    return {};
  }

  $('saju-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    if (state.submitting) return;

    const dog = readDogForm();
    if (!dog.name || !dog.birth_date) {
      const field = dog.name ? form.dogDate : form.dogName;
      const error = $(`${field.id}-error`);
      field.setAttribute('aria-invalid', 'true');
      error.textContent = dog.name ? `${form.dogDateLabel.textContent}을 입력해 주세요.` : '강아지 이름을 입력해 주세요.';
      error.classList.remove('hidden');
      field.focus();
      return;
    }
    const modeRequest = buildModeRequest();
    if (modeRequest.error) {
      showToast(modeRequest.error);
      return;
    }
    const mode = state.mode;
    const firstTab = state.firstResultTab;
    state.submitting = true;
    btnSubmit.disabled = true;

    try {
      if (!(await requireUserKey()) || activeScreen !== screens.input) return;
      setDogNameDisplays(dog.name);
      showResultLoading(mode, firstTab);
      const registration = await api('/api/saju/dogs/', {
        method: 'POST',
        body: { nickname: 'Toss 사용자', dog },
      });
      const dogRecord = { ...dog, id: registration.dog_id };
      state.selectedDogId = dogRecord.id;
      state.prefilledDogId = dogRecord.id;

      if (mode === 'general') {
        const luck = await loadDailyLuck(dogRecord.id);
        if (activeScreen === screens.loading) showGeneralResult(dogRecord, luck, firstTab);
      } else {
        const result = await api(`/api/saju/dogs/${dogRecord.id}/${modeRequest.path}/`, {
          method: 'POST',
          body: modeRequest.body,
        });
        if (activeScreen !== screens.loading) return;
        if (mode === 'chemistry') {
          showChemistryResult(dogRecord, result);
        } else {
          showFriendResult(dogRecord, result);
        }
      }
      refreshMyDogs();
    } catch (error) {
      console.error(error);
      if (activeScreen === screens.loading) {
        showScreen(screens.input);
        showApiError(error);
      }
    } finally {
      state.submitting = false;
      btnSubmit.disabled = false;
    }
  });

  // ─── 결과 렌더링 ───
  function showResultLoading(mode, firstTab) {
    $('loading-title').textContent = mode !== 'general' ? '궁합을 살펴보고 있어요'
      : firstTab === 'tab-lifetime' ? '평생 사주를 살펴보고 있어요' : '운세 카드를 열고 있어요';
    navigateTo(screens.loading, false);
  }

  function loadDailyLuck(dogId) {
    return api(`/api/saju/dogs/${dogId}/daily-luck/`);
  }

  function renderChips(container, items) {
    container.replaceChildren(...items.map((text) => {
      const chip = document.createElement('span');
      chip.className = 'keyword-chip';
      chip.textContent = text;
      return chip;
    }));
  }

  function renderIljuCard(profile, zodiac) {
    const card = $('ilju-card');
    if (!profile) {
      card.classList.add('hidden');
      return;
    }
    card.classList.remove('hidden');
    $('res-ilju-nickname').textContent = `“${profile.nickname}”`;
    $('res-ilju-pillar').textContent = `${profile.pillar}(${profile.pillar_hanja})일주`;
    const zodiacBadge = $('res-zodiac');
    if (zodiac) {
      const seal = zodiacSeal(zodiac.branch);
      zodiacBadge.replaceChildren(...(seal ? [seal] : []), `${zodiac.label} 댕댕이`);
      zodiacBadge.classList.toggle('has-seal', Boolean(seal));
    }
    zodiacBadge.classList.toggle('hidden', !zodiac);
    $('res-ilju-desc').textContent = profile.description;
    renderChips($('res-ilju-keywords'), (profile.keywords || []).map((k) => `#${k}`));
  }

  function renderLifetime(dog, basics, personality) {
    updateSajuTable(basics);
    const info = elementInfo(basics.main_element);
    setMinhwaPortrait($('result-img'), dog.breed, basics.main_element);
    $('res-summary').innerHTML = `${formatText(personality.personality_summary)}<br><span class="${info.className}">${escapeHtml(elementLabel(basics.main_element))}</span>의 기운을 타고난 <span class="dog-name-display">${escapeHtml(dog.name)}</span>!`;
    const reports = [
      ['res-food', personality.treat_luck],
      ['res-energy', personality.vitality_analysis],
      ['res-love', personality.care_tips],
      ['res-social', personality.social_analysis],
    ];
    for (const [id, text] of reports) {
      const report = $(id);
      report.closest('details').open = false;
      report.innerHTML = formatLetterParagraphs(text) || '<p>아직 풀이가 없어요.</p>';
    }
    $('res-estimated-note').classList.toggle('hidden', !personality.is_estimated_birth);
    renderIljuCard(personality.day_pillar_profile, personality.zodiac);
  }

  function renderToday(dog, luck) {
    const date = luck.date || todayIso();
    const dateLabel = $('res-luck-date');
    dateLabel.dateTime = date;
    dateLabel.textContent = fortuneDate(date);
    $('res-daily-title').textContent = `${dog.name}의 오늘 운세`;
    setMinhwaPortrait($('res-daily-dog'), dog.breed, luck.today_element || dog.main_element);
    $('res-luck-score').textContent = luck.luck_score;
    const message = (luck.message || '').trim();
    const firstParagraph = message.split(/\r?\n\s*\r?\n/, 1)[0];
    const firstSentence = firstParagraph.match(/^.*?[.!?。！？](?=\s|$)/su)?.[0];
    const lead = (firstParagraph.length > 100 && firstSentence) ? firstSentence : firstParagraph;
    const detail = message.slice(lead.length).trim();
    $('res-luck-msg').innerHTML = formatText(lead);
    $('res-luck-detail').innerHTML = formatLetterParagraphs(detail);
    const theme = $('res-luck-theme');
    theme.classList.toggle('hidden', !ELEMENTS[luck.today_element]);
    if (ELEMENTS[luck.today_element]) {
      theme.replaceChildren(elementIcon(luck.today_element), `오늘의 기운 · ${elementLabel(luck.today_element)}`);
    }
    const more = $('res-luck-more');
    more.open = false;
    more.classList.toggle('hidden', !detail);
    $('res-luck-color').textContent = luck.lucky_color;
    $('res-luck-dir').textContent = luck.lucky_direction;
    const dayNumber = Math.floor(Date.parse(`${date}T00:00:00Z`) / 86400000);
    $('res-daily-mission').textContent = DAILY_MISSIONS[(dayNumber + Number(dog.id)) % DAILY_MISSIONS.length];
  }

  function showGeneralResult(dog, luck, firstTab) {
    state.mode = 'general';
    state.currentDog = dog;
    state.dailyLuck = luck;
    state.lifetime = { loading: false, loaded: false };
    $('lifetime-report').classList.add('hidden');
    setDogNameDisplays(dog.name);
    renderToday(dog, luck);
    renderAttendanceStatus();
    prepareResultScreen(firstTab);
    navigateTo(screens.result);
    stampAttendanceForToday();
  }

  async function loadLifetime() {
    const result = state.lifetime;
    if (!result || result.loading || result.loaded) return;
    const dog = state.currentDog;
    const status = $('lifetime-status');
    const retry = $('btn-retry-lifetime');
    result.loading = true;
    status.textContent = '평생 사주를 불러오고 있어요.';
    status.classList.remove('hidden');
    retry.classList.add('hidden');

    try {
      const [basics, personality] = await Promise.all([
        api(`/api/saju/dogs/${dog.id}/basics/`),
        api(`/api/saju/dogs/${dog.id}/personality/`),
      ]);
      if (state.lifetime !== result || state.currentDog !== dog) return;
      dog.main_element = basics.main_element;
      dog.nickname = personality.day_pillar_profile?.nickname || null;
      renderLifetime(dog, basics, personality);
      setElementBars(basics.element_distribution);
      renderRadarChart(basics.element_distribution);
      result.loaded = true;
      status.classList.add('hidden');
      $('lifetime-report').classList.remove('hidden');
      if ($('tab-lifetime').classList.contains('active')) {
        updateShareButton();
        revealCards();
        animateBars();
      }
    } catch (error) {
      if (state.lifetime !== result || state.currentDog !== dog) return;
      status.textContent = apiErrorMessage(error) || '평생 사주를 불러오지 못했어요.';
      retry.classList.remove('hidden');
    } finally {
      result.loading = false;
    }
  }

  $('btn-retry-lifetime').addEventListener('click', loadLifetime);

  function renderZodiacLine(element, zodiac, firstName, secondName) {
    if (!zodiac) {
      element.classList.add('hidden');
      return;
    }
    const bonus = zodiac.bonus > 0 ? ` (+${zodiac.bonus}점)` : (zodiac.bonus < 0 ? ` (${zodiac.bonus}점)` : '');
    element.replaceChildren(
      document.createTextNode(`🐾 ${zodiac.first} ${firstName} × ${zodiac.second} ${secondName} · ${zodiac.label || zodiac.type}${bonus}`),
      document.createElement('br'),
      document.createTextNode(zodiac.description),
    );
    element.classList.remove('hidden');
  }

  function showChemistryResult(dog, data) {
    state.mode = 'chemistry';
    state.lastChemistry = data;
    state.currentDog = { ...dog, main_element: data.dog_element };
    setDogNameDisplays(dog.name);

    $('res-chem-score').textContent = data.score ?? '--';
    $('res-chem-title').textContent = data.title || '궁합 결과';
    setElementLabel($('res-chem-owner-element'), data.owner_element);
    setElementLabel($('res-chem-dog-element'), data.dog_element);
    renderCompatibilityRelation($('res-chem-rel'), data.relationship_type);
    $('res-chem-desc').innerHTML = formatText(data.description || '');
    const advice = $('res-chem-advice');
    if (data.advice) {
      advice.innerHTML = `<strong>💡 이렇게 해보세요</strong><br>${formatText(data.advice)}`;
      advice.style.display = 'block';
    } else {
      advice.style.display = 'none';
    }
    renderZodiacLine($('res-chem-zodiac'), data.zodiac, dog.name, '보호자님');

    prepareResultScreen();
    navigateTo(screens.result);
    // 풀이 잠금 해제용 광고는 결과를 띄운 뒤에 미리 불러둠
    // (메인 배너가 내려간 다음이라야 안드로이드에서 두 광고의 이벤트가 섞여 유실되지 않음)
    setTimeout(preloadFullScreenAd, 400);
  }

  function showFriendResult(dog, data) {
    state.mode = 'friend';
    state.lastFriend = data;
    state.currentDog = { ...dog, main_element: data.my_element };
    setDogNameDisplays(dog.name);

    $('res-friend-title').textContent = data.title;
    setElementLabel($('res-friend-my-element'), data.my_element);
    $('res-friend-name').textContent = data.friend_name;
    setElementLabel($('res-friend-element'), data.friend_element);
    renderCompatibilityRelation($('res-friend-rel'), data.relationship_type);
    $('res-friend-score').textContent = data.score;
    $('res-friend-desc').textContent = data.description;
    $('res-friend-tip').textContent = `💡 ${data.tip}`;
    renderZodiacLine($('res-friend-zodiac'), data.zodiac, dog.name, data.friend_name);

    const profileLine = $('res-friend-profile');
    if (data.friend_profile) {
      profileLine.textContent = `참고로 ${withJosa(data.friend_name, '은/는')} “${data.friend_profile.nickname}”(${data.friend_profile.pillar}일주) 캐릭터래요!`;
      profileLine.classList.remove('hidden');
    } else {
      profileLine.classList.add('hidden');
    }

    prepareResultScreen();
    navigateTo(screens.result);
  }

  // 사주 표 파싱
  function updateSajuTable(data) {
    const splitChar = (str) => {
      if (!str || str === '알수없음') return ['-', '-'];
      return [str.charAt(0) || '-', str.charAt(1) || '-'];
    };

    const y = splitChar(data.year_pillar);
    const m = splitChar(data.month_pillar);
    const d = splitChar(data.day_pillar);
    const h = splitChar(data.hour_pillar || '--');

    $('stem-year').innerHTML = `<span class="hanja">年</span><br>${escapeHtml(y[0])}`;
    $('stem-month').innerHTML = `<span class="hanja">月</span><br>${escapeHtml(m[0])}`;
    $('stem-day').innerHTML = `<span class="hanja">日</span><br>${escapeHtml(d[0])}`;
    $('stem-hour').innerHTML = `<span class="hanja">時</span><br>${escapeHtml(h[0])}`;

    $('branch-year').innerHTML = `<span class="hanja">年</span><br>${escapeHtml(y[1])}`;
    $('branch-month').innerHTML = `<span class="hanja">月</span><br>${escapeHtml(m[1])}`;
    $('branch-day').innerHTML = `<span class="hanja">日</span><br>${escapeHtml(d[1])}`;
    $('branch-hour').innerHTML = `<span class="hanja">時</span><br>${escapeHtml(h[1])}`;
  }

  // 오행 막대 그래프: 너비는 바로 정하고, 채워지는 효과는 animateBars()가 transform으로 처리
  function setElementBars(dist) {
    const values = { wood: dist['목'] || 0, fire: dist['화'] || 0, earth: dist['토'] || 0, metal: dist['금'] || 0, water: dist['수'] || 0 };
    Object.entries(values).forEach(([slug, value]) => {
      $(`val-${slug}`).textContent = `${value}%`;
      $(`bar-${slug}`).style.width = `${value}%`;
    });
  }

  // 레이더 차트: 축이 5개뿐이라 라이브러리 없이 SVG로 그림 (Chart.js 다운로드·렌더 비용 제거)
  // 커지며 나타나는 효과는 CSS 애니메이션이라, 평생 사주 탭이 보일 때마다 자동으로 재생됨
  const RADAR_AXES = [['목', '목(木)'], ['화', '화(火)'], ['토', '토(土)'], ['금', '금(金)'], ['수', '수(水)']];
  const SVG_NS = 'http://www.w3.org/2000/svg';

  function svgEl(name, attrs) {
    const el = document.createElementNS(SVG_NS, name);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
    return el;
  }

  function renderRadarChart(dist) {
    const values = RADAR_AXES.map(([key]) => Number(dist[key]) || 0);
    // Chart.js 기본 눈금과 같게: 50% 이하는 5 단위, 그 이상은 10 단위로 고리를 그림
    const peak = Math.max(...values);
    const step = peak > 50 ? 10 : 5;
    const max = Math.max(step, Math.ceil(peak / step) * step);
    const rings = max / step;
    const cx = 150;
    const cy = 125;
    const radius = 98;
    const pointAt = (index, r) => {
      const angle = -Math.PI / 2 + (index * 2 * Math.PI) / RADAR_AXES.length;
      return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
    };
    const toPoints = (radii) => radii.map((r, i) => pointAt(i, r).map((n) => n.toFixed(1)).join(',')).join(' ');

    const nodes = [];
    for (let level = 1; level <= rings; level += 1) {
      nodes.push(svgEl('polygon', { points: toPoints(RADAR_AXES.map(() => (radius * level) / rings)), class: 'radar-grid' }));
    }
    RADAR_AXES.forEach((_, i) => {
      const [x, y] = pointAt(i, radius);
      nodes.push(svgEl('line', { x1: cx, y1: cy, x2: x.toFixed(1), y2: y.toFixed(1), class: 'radar-grid' }));
    });

    const data = svgEl('g', { class: 'radar-data' });
    const dataRadii = values.map((v) => (radius * v) / max);
    data.appendChild(svgEl('polygon', { points: toPoints(dataRadii), class: 'radar-area' }));
    dataRadii.forEach((r, i) => {
      const [x, y] = pointAt(i, r);
      data.appendChild(svgEl('circle', { cx: x.toFixed(1), cy: y.toFixed(1), r: 5, class: 'radar-point' }));
    });
    nodes.push(data);

    RADAR_AXES.forEach(([, label], i) => {
      const [x, y] = pointAt(i, radius + 18);
      const anchor = Math.abs(x - cx) < 1 ? 'middle' : (x > cx ? 'start' : 'end');
      const text = svgEl('text', { x: x.toFixed(1), y: (y + (y > cy ? 6 : 0)).toFixed(1), 'text-anchor': anchor, class: 'radar-label' });
      text.textContent = label;
      nodes.push(text);
    });

    const svg = $('radar-chart');
    svg.replaceChildren(...nodes);
    svg.setAttribute('aria-label', `오행 밸런스: ${RADAR_AXES.map(([key], i) => `${key} ${values[i]}%`).join(', ')}`);
  }

  function animateBars() {
    const bars = document.querySelectorAll('.bar-fill');
    bars.forEach((bar) => {
      bar.style.transition = 'none';
      bar.style.transform = 'translateX(-101%)';
    });
    setTimeout(() => {
      bars.forEach((bar) => {
        bar.style.transition = 'transform 1.2s cubic-bezier(0.25, 1, 0.5, 1)';
        bar.style.transform = 'translateX(0)';
      });
    }, 50);
  }

  // ─── 재방문: 내 강아지 ───
  function renderMyDogs() {
    const chipList = $('my-dog-chips');
    chipList.classList.toggle('hidden', !state.myDogs.length);

    function updateSelectedDog() {
      const dog = getSelectedDog() || state.myDogs[0];
      setMinhwaPortrait($('my-dog-today-img'), dog?.breed, dog?.main_element);
      $('home-dog-status').classList.toggle('hidden', !dog);
      chipList.querySelectorAll('[data-dog-id]').forEach((chip) => {
        const selected = chip.dataset.dogId === String(dog?.id);
        chip.classList.toggle('active', selected);
        chip.setAttribute('aria-pressed', String(selected));
      });
      renderTodayBadge();
    }

    const chips = state.myDogs.map((item) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'dog-chip';
      chip.dataset.dogId = item.id;
      chip.textContent = item.name;
      chip.addEventListener('click', () => {
        state.selectedDogId = item.id;
        updateSelectedDog();
      });
      return chip;
    });
    const addChip = document.createElement('button');
    addChip.type = 'button';
    addChip.className = 'dog-chip';
    addChip.textContent = '+ 강아지 추가';
    addChip.addEventListener('click', () => {
      state.selectedDogId = 'new';
      openInput('general');
    });
    chipList.replaceChildren(...chips, addChip);
    updateSelectedDog();
  }

  async function refreshMyDogs() {
    const key = await userKeyReady;
    if (!key) return;
    try {
      const data = await api('/api/saju/me/dogs/');
      state.myDogs = data.dogs || [];
      if (state.selectedDogId !== 'new' && !state.myDogs.some((dog) => dog.id === state.selectedDogId)) {
        state.selectedDogId = state.myDogs[0]?.id ?? null;
      }
      renderMyDogs();
      if (state.myDogs.length && state.attendanceDate !== todayIso()) refreshAttendanceSummary();
    } catch (error) {
      console.warn('[MyDogs] load failed', error);
    }
  }

  async function openMyFortune(firstTab = 'tab-today') {
    if (state.submitting) return;
    const origin = activeScreen;
    const button = $('btn-my-dog-today');
    state.submitting = true;
    button.disabled = true;
    try {
      await withTimeout(initialDogs, 1800);
      if (activeScreen !== origin) return;
      const dog = getSelectedDog() || state.myDogs[0];
      if (!dog) {
        openInput('general', firstTab);
        return;
      }
      if (!(await requireUserKey()) || activeScreen !== origin) return;
      showResultLoading('general', firstTab);
      const luck = await loadDailyLuck(dog.id);
      if (activeScreen === screens.loading) showGeneralResult(dog, luck, firstTab);
    } catch (error) {
      console.error(error);
      if (activeScreen === screens.loading) {
        showScreen(origin);
        if (error instanceof ApiError && error.status === 404) refreshMyDogs();
        showApiError(error);
      }
    } finally {
      state.submitting = false;
      button.disabled = false;
    }
  }

  $('btn-my-dog-today').addEventListener('click', () => openMyFortune());

  // ─── 출석 ───
  function attendanceTotal(data) {
    return data.total_days ?? data.streak_count ?? (data.attended_days || []).length;
  }

  function renderTodayBadge() {
    const badge = $('my-dog-today-badge');
    const data = state.attendanceDate === todayIso() ? state.attendance : null;
    badge.classList.toggle('hidden', !data?.already_stamped_today);
  }

  function renderAttendanceStatus() {
    const status = $('attendance-status');
    const data = state.attendanceDate === todayIso() ? state.attendance : null;
    if (!data) {
      status.textContent = '';
      return;
    }
    const streak = data.streak_days || 0;
    if (!data.already_stamped_today) {
      status.textContent = `이번 달 ${attendanceTotal(data)}일`;
      return;
    }
    status.replaceChildren(
      `오늘 발도장 완료 · 이번 달 ${attendanceTotal(data)}일`,
      ...(streak > 1 ? [' · ', streakMedal(streak), `${streak}일 연속`] : []),
    );
  }

  function applyAttendance(data, date = todayIso()) {
    state.attendance = data;
    state.attendanceDate = date;
    renderAttendanceStatus();
    renderTodayBadge();
    if (!$('attendance-modal').classList.contains('hidden')) renderCalendar();
  }

  async function refreshAttendanceSummary() {
    const date = todayIso();
    const previous = state.attendance;
    try {
      const data = await api('/api/saju/attendance/');
      if (state.attendance === previous) applyAttendance(data, date);
    } catch (error) {
      console.warn('[Attendance] load failed', error);
    }
  }

  async function celebrate() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    try {
      const confetti = await loadConfetti();
      confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, colors: ['#FF69B4', '#FFD700', '#ffffff'] });
    } catch (error) {
      console.warn('[Confetti] load failed', error);
    }
  }

  async function stampAttendance({ fromCard = false } = {}) {
    const data = await api('/api/saju/attendance/', { method: 'POST', body: {} });
    applyAttendance(data);
    if (data.stamped && !fromCard) {
      celebrate();
      if (data.new_milestone) setTimeout(() => showTalisman(data.new_milestone), 1400);
    }
    return data;
  }

  // 오늘 운세를 보면 자동으로 출석 처리
  async function stampAttendanceForToday() {
    if (state.attendanceDate === todayIso() && state.attendance?.already_stamped_today) return;
    try {
      await stampAttendance({ fromCard: true });
    } catch (error) {
      console.warn('[Attendance] auto stamp failed', error);
    }
  }

  function renderCalendar() {
    const data = state.attendance || { attended_days: [], streak_days: 0 };
    const attendedDays = data.attended_days || [];
    const total = attendanceTotal(data);
    const [todayYear, todayMonth, todayDate] = todayIso().split('-').map(Number);
    const year = data.year || todayYear;
    const month = data.month || todayMonth;
    const daysInMonth = new Date(year, month, 0).getDate();

    $('calendar-streak').textContent = `${total}일`;
    const run = $('calendar-run');
    const streak = data.streak_days || 0;
    if (streak > 1) {
      run.replaceChildren(streakMedal(streak), `${streak}일 연속 출석 중이에요`);
    } else {
      run.textContent = '';
    }
    run.classList.toggle('hidden', streak <= 1);

    const nextReward = MILESTONES.find((m) => m > total);
    $('calendar-progress-text').textContent = nextReward
      ? `다음 부적까지 ${nextReward - total}일`
      : '이번 달 부적을 모두 모았어요.';
    $('calendar-progress-fill').style.width = `${nextReward ? Math.min((total / nextReward) * 100, 100) : 100}%`;

    const cells = [];
    for (let day = 1; day <= daysInMonth; day += 1) {
      const isStamped = attendedDays.includes(day);
      const cell = document.createElement('div');
      cell.className = 'calendar-cell';
      if (isStamped) cell.classList.add('stamped');
      if (day === todayDate && !isStamped) cell.classList.add('today-pending');

      const span = document.createElement('span');
      span.className = 'day-number';
      span.textContent = day;
      cell.appendChild(span);

      if (isStamped) {
        const stamp = document.createElement('div');
        stamp.className = 'paw-stamp';
        stamp.textContent = '🐾';
        cell.appendChild(stamp);
      }
      cells.push(cell);
    }
    $('calendar-grid').replaceChildren(...cells);

    const stampButton = $('btn-attendance-stamp');
    const alreadyStamped = Boolean(data.already_stamped_today);
    stampButton.disabled = alreadyStamped;
    stampButton.textContent = alreadyStamped ? '오늘 발도장 완료' : '오늘 발도장 찍기';
  }

  $('btn-open-attendance').addEventListener('click', async () => {
    if (!(await requireUserKey())) return;
    try {
      applyAttendance(await api('/api/saju/attendance/'));
    } catch (error) {
      showApiError(error);
      return;
    }
    renderCalendar();
    $('attendance-modal').classList.remove('hidden');
  });

  $('btn-attendance-stamp').addEventListener('click', async () => {
    if (state.attendance?.already_stamped_today) return;
    try {
      await stampAttendance();
    } catch (error) {
      showApiError(error);
    }
  });

  $('btn-close-attendance').addEventListener('click', () => {
    $('attendance-modal').classList.add('hidden');
  });

  // ─── 부적 ───
  const talismanModal = $('talisman-modal');
  let currentTalismanDay = null;

  // 모달에는 화면 크기에 맞춘 가벼운 이미지, '부적 저장하기'는 고화질 원본(PNG)
  const talismanDisplayUrl = (milestone) => `/assets/talisman_${milestone}.webp`;
  const talismanOriginalUrl = (milestone) => `/assets/talisman_${milestone}.png`;

  async function showTalisman(milestone) {
    const reward = TALISMAN_REWARDS[milestone];
    if (!reward) return;
    currentTalismanDay = milestone;
    $('talisman-name').textContent = reward.name;
    $('talisman-desc').textContent = reward.desc;
    const imgEl = $('talisman-img');
    imgEl.onerror = () => { imgEl.style.display = 'none'; };
    imgEl.style.display = 'block';
    imgEl.src = talismanDisplayUrl(milestone);
    // 모달이 뜨는 순간 이미지 디코딩으로 멈추지 않도록 미리 디코딩
    try {
      await imgEl.decode();
    } catch {
      // 디코딩에 실패해도 모달은 띄움 (onerror에서 이미지 숨김)
    }
    talismanModal.classList.remove('hidden');
  }

  talismanModal.addEventListener('click', () => talismanModal.classList.add('hidden'));
  $('talisman-content-wrapper').addEventListener('click', (event) => event.stopPropagation());
  $('btn-close-talisman').addEventListener('click', () => talismanModal.classList.add('hidden'));

  const imageModal = $('image-modal');
  const generatedImage = $('generated-image');

  function openImageSaveModal(imageUrl) {
    generatedImage.src = imageUrl;
    imageModal.style.display = 'flex';
  }

  function closeImageSaveModal() {
    imageModal.style.display = 'none';
    generatedImage.removeAttribute('src');
  }

  $('close-modal').addEventListener('click', closeImageSaveModal);
  imageModal.addEventListener('click', (event) => {
    if (event.target === imageModal) closeImageSaveModal();
  });

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = typeof reader.result === 'string' ? reader.result : '';
        resolve(result.includes(',') ? result.split(',')[1] : result);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  const btnDownloadTalisman = $('btn-download-talisman');
  btnDownloadTalisman.addEventListener('click', async () => {
    const originalText = btnDownloadTalisman.textContent;
    btnDownloadTalisman.textContent = '저장 중...';
    try {
      const response = await fetch(talismanOriginalUrl(currentTalismanDay || 1), { cache: 'no-store' });
      if (!response.ok) throw new Error('Failed to fetch talisman image');
      const blob = await response.blob();

      try {
        await saveBase64Data({
          data: await blobToBase64(blob),
          fileName: `daengsaju_talisman_${currentTalismanDay || 1}.png`,
          mimeType: 'image/png',
        });
        showToast('부적 이미지를 저장했어요 🧧');
      } catch (bridgeError) {
        console.warn('saveBase64Data failed, falling back to image modal', bridgeError);
        const objectUrl = URL.createObjectURL(blob);
        openImageSaveModal(objectUrl);
        setTimeout(() => URL.revokeObjectURL(objectUrl), 60 * 1000);
      }
    } catch (error) {
      console.error(error);
      showToast('이미지 저장에 실패했어요. 잠시 후 다시 시도해주세요.');
    } finally {
      btnDownloadTalisman.textContent = originalText;
    }
  });

  // ─── 공유 ───
  function buildShareMessage() {
    const dog = state.currentDog;
    if (state.mode === 'chemistry' && state.lastChemistry) {
      return `나와 ${dog.name}의 궁합은 ${state.lastChemistry.score}점이래요! 💑\n보호자님도 우리 아이와의 궁합을 확인해 보세요🐾`;
    }
    if (state.mode === 'friend' && state.lastFriend) {
      return `${withJosa(dog.name, '와/과')} ${state.lastFriend.friend_name}의 댕친 궁합은 ${state.lastFriend.score}점! “${state.lastFriend.title}” 🐶\n우리 아이와 친구 강아지의 케미도 확인해 보세요🐾`;
    }
    const intro = dog.nickname
      ? `“${dog.nickname}” 일주 캐릭터래요!`
      : `${elementLabel(dog.main_element)} 기운을 타고났어요!`;
    return `${withJosa(dog.name, '은/는')} ${intro}\n보호자님도 우리 아이 사주를 한 번 알아보세요🐾`;
  }

  btnShare.addEventListener('click', async () => {
    const dog = state.currentDog;
    if (!dog || state.sharing || btnShare.disabled) return;
    const daily = state.mode === 'general' && $('tab-today').classList.contains('active') ? state.dailyLuck : null;
    const message = daily
      ? `${fortuneDate(daily.date || todayIso())}, ${dog.name}의 산책운은 ${daily.luck_score}점 🐾\n우리 강아지 오늘 운세도 뽑아 보세요!`
      : buildShareMessage();
    const element = daily?.today_element || dog.main_element;
    state.sharing = true;
    updateShareButton();

    try {
      let link = APP_SCHEME;
      if (!daily) {
        const { token } = await api(`/api/saju/dogs/${dog.id}/share/`, { method: 'POST', body: {} });
        link += `?share=${encodeURIComponent(token)}`;
      }
      // 링크 미리보기 썸네일: 백엔드가 고정 URL로 제공하는 오행별 공유 카드(1200×630, scripts/og 로 생성)
      const ogImageUrl = `${API_BASE_URL}/static/assets/og_${elementInfo(element).slug}.jpg`;
      const tossLink = await getTossShareLink(link, ogImageUrl);
      await share({ message: `${message}\n\n${tossLink}` });
    } catch (error) {
      console.error(error);
      showToast(error instanceof ApiError
        ? (apiErrorMessage(error) || '공유 링크를 만들지 못했어요. 잠시 후 다시 시도해주세요.')
        : '공유하기는 토스 앱에서 사용할 수 있어요.');
    } finally {
      state.sharing = false;
      updateShareButton();
    }
  });

  // 공유 링크로 들어온 경우: 친구의 공개 카드
  function renderSharedCard(card) {
    setMinhwaPortrait($('share-img'), card.breed, card.main_element);
    $('share-dog-name').textContent = card.dog_name;
    $('share-nickname').textContent = card.profile
      ? `“${card.profile.nickname}”`
      : `${elementLabel(card.main_element)} 기운의 댕댕이`;
    $('share-pillar').textContent = [
      card.profile && `${card.profile.pillar}(${card.profile.pillar_hanja})일주`,
      `${elementLabel(card.main_element)} 기운`,
      card.zodiac?.label,
    ].filter(Boolean).join(' · ');
    $('share-summary').innerHTML = formatText(card.personality_summary || card.profile?.description || '');
    renderChips($('share-keywords'), (card.profile?.keywords || []).map((k) => `#${k}`));
  }

  async function openSharedCard(token) {
    try {
      const card = await api(`/api/saju/share/${encodeURIComponent(token)}/`);
      if (activeScreen !== screens.main) return;
      renderSharedCard(card);
      navigateTo(screens.share);
    } catch (error) {
      console.warn('[Share] card load failed', error);
      showToast('공유된 카드를 찾을 수 없어요. 우리 아이 사주를 직접 확인해 보세요!');
    }
  }

  // ─── 시작 ───
  history.replaceState(null, '', window.location.pathname + window.location.search);
  showScreen(screens.main);

  const shareToken = readShareToken();
  if (shareToken) openSharedCard(shareToken);
  const initialDogs = refreshMyDogs();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

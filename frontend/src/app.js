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

// 로컬 개발 시 VITE_API_BASE_URL 로 로컬 백엔드를 가리킬 수 있음
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'https://web-production-285b5.up.railway.app').replace(/\/+$/, '');
const APP_SCHEME = 'intoss://daengsaju';
const USER_KEY_TIMEOUT_MS = 4000;
const DEV_USER_KEY_STORAGE = 'daengsaju_dev_user_key';
const BANNER_AD_ID = 'ait.v2.live.82786c3925d743b3';
const INTERSTITIAL_AD_ID = 'ait.v2.live.3c235f3d3a424553';
const DEFAULT_ERROR_MESSAGE = '서버 댕댕이가 간식을 먹으러 가서\n잠시 지연되고 있어요 🐾\n잠시 후 다시 시도해주세요.';

const ELEMENTS = {
  '목': { slug: 'wood', hanja: '木', className: 'text-wood' },
  '화': { slug: 'fire', hanja: '火', className: 'text-fire' },
  '토': { slug: 'earth', hanja: '土', className: 'text-earth' },
  '금': { slug: 'metal', hanja: '金', className: 'text-metal' },
  '수': { slug: 'water', hanja: '水', className: 'text-water' },
};
const DEFAULT_ELEMENT = '화';

const MODE_COPY = {
  general: { title: '우리아이의 타고난<br>기질을 알아볼까요?', submit: '운세 보기', share: '운세 공유하기' },
  chemistry: { title: '보호자와 댕댕이의<br>상생 궁합은?', submit: '궁합 보기', share: '궁합 결과 공유하기' },
  friend: { title: '우리 아이와 친구 강아지의<br>댕친 궁합은?', submit: '댕친 궁합 보기', share: '댕친 궁합 공유하기' },
};

// 출석 부적: 이번 달 누적 출석 일수 기준
const MILESTONES = [1, 3, 5, 7, 10, 15, 20];
const TALISMAN_REWARDS = {
  1: { name: '시작의 코기 부적', desc: '첫 출석 완료! 오늘의 시작마다 산뜻한 행운이 따라붙을 거예요.' },
  3: { name: '초심자의 뼈다귀 부적', desc: '이번 달 3번째 출석! 멍멍이의 에너지가 솟아납니다.' },
  5: { name: '복슬복슬 말티즈 부적', desc: '이번 달 5번째 출석! 포근한 기운이 차곡차곡 쌓이고 있어요.' },
  7: { name: '행운의 댕댕 부적', desc: '럭키 7번째 출석! 기분 좋은 일이 가득할 거예요.' },
  10: { name: '재물운 명탐정 부적', desc: '이번 달 10번째 출석! 생각지도 못한 간식이나 행운이 찾아옵니다.' },
  15: { name: '대박 황금 부적', desc: '이번 달 15번째 출석! 주변에서 많은 복이 찾아오는 시기예요.' },
  20: { name: '전설의 댕댕 부적', desc: '이번 달 20번째 출석! 당신은 진정한 댕사주 마스터!' },
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

function elementInfo(element) {
  return ELEMENTS[element] || ELEMENTS[DEFAULT_ELEMENT];
}

function elementLabel(element) {
  const info = ELEMENTS[element];
  return info ? `${element}(${info.hanja})` : (element || '-');
}

function dogImageUrl(element) {
  return `./assets/${elementInfo(element).slug}_dog.webp`;
}

function todayIso() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
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
    submitting: false,
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
  function activateTab(tabId) {
    tabBtns.forEach((b) => b.classList.toggle('active', b.dataset.tab === tabId));
    tabContents.forEach((c) => c.classList.toggle('active', c.id === tabId));

    const scrollContainer = document.querySelector('.result-scroll');
    if (scrollContainer) scrollContainer.scrollTop = 0;

    revealCards();
    if (tabId === 'tab-lifetime') animateBars();
  }

  tabBtns.forEach((btn) => {
    btn.addEventListener('click', () => activateTab(btn.dataset.tab));
  });

  function revealCards() {
    const cards = document.querySelectorAll('.tab-content.active .fade-in');
    cards.forEach((c) => c.classList.remove('reveal'));
    cards.forEach((card, index) => {
      setTimeout(() => card.classList.add('reveal'), index * 150);
    });
  }

  // ─── 네비게이션 ───
  // 메인은 해시 없이 두어야 토스 네이티브 뒤로가기가 앱 종료 확인을 띄움
  window.addEventListener('popstate', () => {
    const hash = window.location.hash.replace('#', '') || 'main-screen';
    showScreen($(hash) || screens.main);
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
    document.querySelectorAll('.screen').forEach((s) => {
      if (s === screenElement) return;
      s.classList.remove('active');
      // 페이드아웃이 끝난 뒤 레이아웃에서 빼서 메모리 절약.
      // 첫 프레임이 늦게 그려져도 지금 보여줄 화면은 숨기지 않도록 클래스 대신 activeScreen으로 판단
      setTimeout(() => {
        if (s !== activeScreen) {
          s.style.display = 'none';
        }
      }, 350);
    });

    screenElement.style.display = 'flex';

    let activated = false;
    const activate = () => {
      // 이미 처리했거나 그 사이 다른 화면으로 전환됐다면 무시
      if (activated || activeScreen !== screenElement) return;
      activated = true;
      screenElement.classList.add('active');

      // 결과 화면은 배경이 불투명하므로 무거운 배경 애니메이션을 숨김
      const bgBlobs = document.querySelector('.bg-blobs');
      if (bgBlobs) bgBlobs.style.display = screenElement === screens.result ? 'none' : 'block';

      // 배너는 메인화면에서만
      if (screenElement === screens.main) {
        mountTossBanner();
      } else {
        unmountTossBanner();
      }
    };
    // requestAnimationFrame을 두 번 중첩해 레이아웃 병목을 줄이고 부드럽게 페이드인
    requestAnimationFrame(() => requestAnimationFrame(activate));
    // 웹뷰가 가려져 rAF가 멈춘 상태에서도 화면이 비지 않도록 타이머로 한 번 더 보장
    setTimeout(activate, 150);
  }

  // 새 결과를 띄우기 직전에 모드별 레이아웃을 맞춤
  function prepareResultScreen() {
    const isGeneral = state.mode === 'general';
    const tabNav = document.querySelector('.tab-nav');
    if (tabNav) tabNav.style.display = isGeneral ? 'flex' : 'none';
    $('tab-today').style.display = isGeneral ? '' : 'none';
    $('tab-lifetime').style.display = isGeneral ? '' : 'none';
    chemistrySection.style.display = state.mode === 'chemistry' ? 'block' : 'none';
    friendSection.style.display = state.mode === 'friend' ? 'block' : 'none';
    btnShare.textContent = MODE_COPY[state.mode].share;

    lockChemReport();
    if (isGeneral) {
      activateTab('tab-today');
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
      variant: 'expanded',
      theme: 'dark',
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

  // ─── 전면 광고 (궁합 상세 해석 잠금 해제) ───
  let interstitialAdLoaded = false;
  let interstitialUnregister = null;

  function preloadInterstitialAd() {
    // isSupported()는 토스 웹뷰에서만 동작 - try-catch 필수
    try {
      if (typeof loadFullScreenAd.isSupported === 'function' && !loadFullScreenAd.isSupported()) {
        return;
      }
    } catch {
      return; // 웹뷰 외부(일반 브라우저) 환경
    }

    if (interstitialUnregister) {
      interstitialUnregister();
      interstitialUnregister = null;
    }
    interstitialAdLoaded = false;

    interstitialUnregister = loadFullScreenAd({
      options: { adGroupId: INTERSTITIAL_AD_ID },
      onEvent: (event) => {
        if (event.type === 'loaded') interstitialAdLoaded = true;
      },
      onError: (err) => {
        console.error('[Interstitial] load error:', err);
        interstitialAdLoaded = false;
      },
    });
  }

  preloadInterstitialAd();

  /** 전면 광고를 보여준 뒤 callback 실행. 미지원이거나 아직 로드 전이면 바로 실행 */
  function showInterstitialThenDo(callback) {
    let isSupported = false;
    try {
      isSupported = typeof showFullScreenAd.isSupported === 'function' ? showFullScreenAd.isSupported() : true;
    } catch {
      callback();
      return;
    }

    if (!isSupported || !interstitialAdLoaded) {
      callback();
      return;
    }

    interstitialAdLoaded = false; // 중복 호출 방지
    const unregisterShow = showFullScreenAd({
      options: { adGroupId: INTERSTITIAL_AD_ID },
      onEvent: (event) => {
        if (event.type === 'dismissed' || event.type === 'failedToShow') {
          if (typeof unregisterShow === 'function') unregisterShow();
          preloadInterstitialAd(); // load→show→load 순환
          callback();
        }
      },
      onError: (err) => {
        console.error('[Interstitial] show error:', err);
        if (typeof unregisterShow === 'function') unregisterShow();
        preloadInterstitialAd();
        callback();
      },
    });
  }

  function lockChemReport() {
    const container = $('locked-chem-container');
    const overlay = $('unlock-chem-overlay');
    if (!container) return;
    container.classList.remove('is-unlocked');
    container.classList.add('is-locked');
    container.querySelectorAll('.lockable-text').forEach((t) => { t.style.filter = ''; });
    if (overlay) {
      overlay.style.opacity = '';
      overlay.style.pointerEvents = '';
      overlay.style.display = 'flex';
    }
  }

  function unlockChemReport() {
    const container = $('locked-chem-container');
    const overlay = $('unlock-chem-overlay');
    if (!container) return;
    container.classList.remove('is-locked');
    container.classList.add('is-unlocked');
    if (overlay) {
      overlay.style.opacity = '0';
      overlay.style.pointerEvents = 'none';
      setTimeout(() => {
        overlay.style.display = 'none';
        // 트랜지션이 끝나면 필터를 완전히 제거 (GPU 메모리 절약)
        container.querySelectorAll('.lockable-text').forEach((t) => { t.style.filter = 'none'; });
      }, 500);
    }
  }

  const btnUnlockChem = $('btn-unlock-chem');
  btnUnlockChem.addEventListener('click', () => {
    if (btnUnlockChem.classList.contains('is-loading')) return;
    btnUnlockChem.classList.add('is-loading');
    btnUnlockChem.textContent = '⏳ 광고 준비 중...';

    showInterstitialThenDo(() => {
      btnUnlockChem.classList.remove('is-loading');
      btnUnlockChem.innerHTML = '<span class="btn-unlock-icon">🎬</span> 광고 보고 전체 풀이 보기';
      unlockChemReport();
    });
  });

  // ─── 입력 폼 ───
  const form = {
    dogName: $('dog-name'),
    dogDate: $('dog-date'),
    dogDateLabel: $('dog-date-label'),
    dogTime: $('dog-time'),
    dogTimeGroup: $('dog-time-group'),
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
    form.dogDateLabel.textContent = estimated ? '입양일 또는 추정 생일' : '강아지 생년월일';
    form.dogTimeGroup.classList.toggle('hidden', estimated);
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
      birth_date: form.dogDate.value,
      birth_time: estimated ? null : (form.dogTime.value || null),
      is_lunar: lunar,
      is_leap_month: lunar && form.dogLeap.checked,
      gender: gender === 'F' ? 'FEMALE' : 'MALE',
      is_estimated_birth: estimated,
    };
  }

  function fillDogForm(dog) {
    form.dogName.value = dog?.name || '';
    form.dogDate.value = dog?.birth_date || '';
    form.dogTime.value = dog?.birth_time ? dog.birth_time.slice(0, 5) : '';
    form.dogEstimated.checked = Boolean(dog?.is_estimated_birth);
    form.dogLunar.checked = Boolean(dog?.is_lunar);
    syncEstimated();
    form.dogLeap.checked = Boolean(dog?.is_leap_month) && form.dogLunar.checked;
    $(dog?.gender === 'FEMALE' ? 'dog-f' : 'dog-m').checked = true;
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

  function openInput(mode) {
    state.mode = mode;
    $('input-title').innerHTML = MODE_COPY[mode].title;
    btnSubmit.textContent = MODE_COPY[mode].submit;
    form.ownerSection.classList.toggle('hidden', mode !== 'chemistry');
    form.friendSection.classList.toggle('hidden', mode !== 'friend');
    prepareDogForm();
    navigateTo(screens.input);
  }

  $('btn-general').addEventListener('click', () => openInput('general'));
  $('btn-chemistry').addEventListener('click', () => openInput('chemistry'));
  $('btn-friend').addEventListener('click', () => openInput('friend'));
  $('btn-share-cta').addEventListener('click', () => openInput('general'));

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

  btnSubmit.addEventListener('click', async (event) => {
    event.preventDefault();
    if (state.submitting) return;

    const dog = readDogForm();
    if (!dog.name || !dog.birth_date) {
      showToast('강아지 이름과 생년월일을 입력해주세요!');
      return;
    }
    const modeRequest = buildModeRequest();
    if (modeRequest.error) {
      showToast(modeRequest.error);
      return;
    }
    if (!(await requireUserKey())) return;

    state.submitting = true;
    setDogNameDisplays(dog.name);
    navigateTo(screens.loading, false);

    try {
      const registration = await api('/api/saju/dogs/', {
        method: 'POST',
        body: { nickname: 'Toss 사용자', dog },
      });
      const dogRecord = { ...dog, id: registration.dog_id };
      state.selectedDogId = dogRecord.id;
      state.prefilledDogId = dogRecord.id;

      if (state.mode === 'general') {
        showGeneralResult(dogRecord, await loadDogBundle(dogRecord.id));
      } else {
        const result = await api(`/api/saju/dogs/${dogRecord.id}/${modeRequest.path}/`, {
          method: 'POST',
          body: modeRequest.body,
        });
        if (state.mode === 'chemistry') {
          showChemistryResult(dogRecord, result);
        } else {
          showFriendResult(dogRecord, result);
        }
      }
      refreshMyDogs();
    } catch (error) {
      console.error(error);
      showScreen(screens.input);
      showApiError(error);
    } finally {
      state.submitting = false;
    }
  });

  // ─── 결과 렌더링 ───
  async function loadDogBundle(dogId) {
    // 각 API가 원국 계산을 스스로 보장하므로 병렬 호출해도 안전
    const [basics, personality, luck] = await Promise.all([
      api(`/api/saju/dogs/${dogId}/basics/`),
      api(`/api/saju/dogs/${dogId}/personality/`),
      api(`/api/saju/dogs/${dogId}/daily-luck/`),
    ]);
    return { basics, personality, luck };
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
    zodiacBadge.textContent = zodiac ? `${zodiac.label} 댕댕이` : '';
    zodiacBadge.classList.toggle('hidden', !zodiac);
    $('res-ilju-desc').textContent = profile.description;
    renderChips($('res-ilju-keywords'), (profile.keywords || []).map((k) => `#${k}`));
  }

  function renderLifetime(dog, basics, personality) {
    updateSajuTable(basics);
    const info = elementInfo(basics.main_element);
    $('result-img').src = dogImageUrl(basics.main_element);
    $('res-summary').innerHTML = `${formatText(personality.personality_summary)}<br><span class="${info.className}">${escapeHtml(elementLabel(basics.main_element))}</span>의 기운을 타고난 <span class="dog-name-display">${escapeHtml(dog.name)}</span>!`;
    $('res-food').innerHTML = formatText(personality.treat_luck);
    $('res-energy').innerHTML = formatText(personality.vitality_analysis);
    $('res-love').innerHTML = formatText(personality.care_tips);
    $('res-social').innerHTML = formatText(personality.social_analysis);
    $('res-estimated-note').classList.toggle('hidden', !personality.is_estimated_birth);
    renderIljuCard(personality.day_pillar_profile, personality.zodiac);
  }

  function renderToday(luck) {
    $('res-luck-score').textContent = luck.luck_score;
    $('res-luck-msg').innerHTML = formatText(luck.message);
    $('res-luck-color').textContent = luck.lucky_color;
    $('res-luck-dir').textContent = luck.lucky_direction;

    const pillarLine = $('res-today-pillar');
    if (luck.today_pillar) {
      pillarLine.textContent = `오늘은 ${luck.today_pillar}(${luck.today_pillar_hanja})일 · ${elementLabel(luck.today_element)} 기운이 흐르는 날`;
      pillarLine.classList.remove('hidden');
    } else {
      pillarLine.classList.add('hidden');
    }
  }

  function showGeneralResult(dog, { basics, personality, luck }) {
    state.mode = 'general';
    state.currentDog = {
      ...dog,
      main_element: basics.main_element,
      nickname: personality.day_pillar_profile?.nickname || null,
    };
    setDogNameDisplays(dog.name);
    renderLifetime(dog, basics, personality);
    renderToday(luck);
    renderAttendanceStatus();
    setElementBars(basics.element_distribution);
    renderRadarChart(basics.element_distribution);
    prepareResultScreen();
    navigateTo(screens.result);
    stampAttendanceForToday();
  }

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
    $('res-chem-owner-element').textContent = elementLabel(data.owner_element);
    $('res-chem-dog-element').textContent = elementLabel(data.dog_element);
    // 쉬운 말(닮은꼴형 등)을 위에, 명리 용어는 아래 작게: 한 줄로 두면 칩이 길어져 양옆 이름이 줄바꿈됨
    const relationChip = $('res-chem-rel');
    const plainLabel = document.createElement('strong');
    plainLabel.textContent = relationPlainLabel(data.relationship_type);
    const termLabel = document.createElement('small');
    termLabel.textContent = data.relationship_type;
    relationChip.replaceChildren(plainLabel, termLabel);
    relationChip.classList.add('two-line');
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
  }

  function showFriendResult(dog, data) {
    state.mode = 'friend';
    state.lastFriend = data;
    state.currentDog = { ...dog, main_element: data.my_element };
    setDogNameDisplays(dog.name);

    $('res-friend-title').textContent = data.title;
    $('res-friend-my-element').textContent = elementLabel(data.my_element);
    $('res-friend-name').textContent = data.friend_name;
    $('res-friend-element').textContent = elementLabel(data.friend_element);
    $('res-friend-rel').textContent = `✨ ${data.relationship_type} 관계 ✨`;
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
    const section = $('my-dog-section');
    if (!state.myDogs.length) {
      section.classList.add('hidden');
      return;
    }
    section.classList.remove('hidden');

    const dog = getSelectedDog() || state.myDogs[0];
    $('my-dog-today-img').src = dogImageUrl(dog.main_element);
    $('my-dog-today-title').textContent = `${dog.name}의 오늘 운세 보기`;
    $('my-dog-today-desc').textContent = dog.nickname
      ? `“${dog.nickname}” ${dog.name}의 오늘 산책운을 확인해 보세요`
      : '탭 한 번이면 출석 도장까지 쾅!';
    renderTodayBadge();

    const chips = state.myDogs.map((item) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = `dog-chip${item.id === dog.id ? ' active' : ''}`;
      chip.textContent = item.name;
      chip.setAttribute('role', 'listitem');
      chip.addEventListener('click', () => {
        state.selectedDogId = item.id;
        renderMyDogs();
      });
      return chip;
    });
    const addChip = document.createElement('button');
    addChip.type = 'button';
    addChip.className = 'dog-chip';
    addChip.textContent = '+ 새 아이';
    addChip.setAttribute('role', 'listitem');
    addChip.addEventListener('click', () => {
      state.selectedDogId = 'new';
      openInput('general');
    });
    $('my-dog-chips').replaceChildren(...chips, addChip);
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
      if (state.myDogs.length && !state.attendance) refreshAttendanceSummary();
    } catch (error) {
      console.warn('[MyDogs] load failed', error);
    }
  }

  async function openDogToday() {
    const dog = getSelectedDog() || state.myDogs[0];
    if (!dog || !(await requireUserKey())) return;
    state.mode = 'general';
    setDogNameDisplays(dog.name);
    navigateTo(screens.loading, false);
    try {
      showGeneralResult(dog, await loadDogBundle(dog.id));
    } catch (error) {
      console.error(error);
      showScreen(screens.main);
      if (error instanceof ApiError && error.status === 404) refreshMyDogs();
      showApiError(error);
    }
  }

  $('btn-my-dog-today').addEventListener('click', openDogToday);

  // ─── 출석 ───
  function attendanceTotal(data) {
    return data.total_days ?? data.streak_count ?? (data.attended_days || []).length;
  }

  function renderTodayBadge() {
    const badge = $('my-dog-today-badge');
    const data = state.attendance;
    if (!data) {
      badge.textContent = '오늘의 산책운 도착 🐾';
      return;
    }
    const streak = data.streak_days || 0;
    if (data.already_stamped_today) {
      badge.textContent = streak > 1 ? `🔥 ${streak}일 연속 출석 중` : '✅ 오늘 출석 완료';
    } else {
      badge.textContent = streak > 0 ? `오늘 보면 ${streak + 1}일 연속 출석!` : '오늘의 산책운 도착 🐾';
    }
  }

  function renderAttendanceStatus() {
    const status = $('attendance-status');
    const data = state.attendance;
    if (!data) {
      status.textContent = '오늘 운세를 보면 출석 도장이 자동으로 찍혀요 🐾';
      return;
    }
    const streak = data.streak_days || 0;
    status.textContent = data.already_stamped_today
      ? `✅ 오늘 출석 완료 · 이번 달 ${attendanceTotal(data)}일${streak > 1 ? ` · 🔥 ${streak}일 연속` : ''}`
      : `이번 달 ${attendanceTotal(data)}일 출석 · 오늘 도장은 아직이에요`;
  }

  function applyAttendance(data) {
    state.attendance = data;
    renderAttendanceStatus();
    renderTodayBadge();
    if (!$('attendance-modal').classList.contains('hidden')) renderCalendar();
  }

  async function refreshAttendanceSummary() {
    try {
      applyAttendance(await api('/api/saju/attendance/'));
    } catch (error) {
      console.warn('[Attendance] load failed', error);
    }
  }

  async function celebrate() {
    try {
      const confetti = await loadConfetti();
      confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, colors: ['#FF69B4', '#FFD700', '#ffffff'] });
    } catch (error) {
      console.warn('[Confetti] load failed', error);
    }
  }

  async function stampAttendance({ quiet = false } = {}) {
    const data = await api('/api/saju/attendance/', { method: 'POST', body: {} });
    applyAttendance(data);
    if (data.stamped) {
      if (!quiet) showToast(`🐾 출석 도장 쾅! 이번 달 ${attendanceTotal(data)}번째 출석이에요`);
      celebrate();
      if (data.new_milestone) setTimeout(() => showTalisman(data.new_milestone), 1400);
    }
    return data;
  }

  // 오늘 운세를 보면 자동으로 출석 처리
  async function stampAttendanceForToday() {
    if (state.attendance?.already_stamped_today) return;
    try {
      await stampAttendance();
    } catch (error) {
      console.warn('[Attendance] auto stamp failed', error);
    }
  }

  function renderCalendar() {
    const data = state.attendance || { attended_days: [], streak_days: 0 };
    const attendedDays = data.attended_days || [];
    const total = attendanceTotal(data);
    const now = new Date();
    const year = data.year || now.getFullYear();
    const month = data.month || now.getMonth() + 1;
    const daysInMonth = new Date(year, month, 0).getDate();
    const todayDate = now.getDate();

    $('calendar-streak').textContent = `${total}일`;
    const run = $('calendar-run');
    const streak = data.streak_days || 0;
    run.textContent = streak > 1 ? `🔥 ${streak}일 연속 출석 중이에요` : '';
    run.classList.toggle('hidden', streak <= 1);

    const nextReward = MILESTONES.find((m) => m > total);
    $('calendar-progress-text').textContent = nextReward
      ? `다음 스페셜 부적까지 ${nextReward - total}일 남았어요!`
      : '이번 달 부적을 모두 모았어요! 🎉';
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
    stampButton.textContent = alreadyStamped ? '오늘 출석 완료' : '오늘 출석하기';
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
      await stampAttendance({ quiet: true });
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
    if (!dog || btnShare.disabled) return;
    const originalText = btnShare.textContent;
    btnShare.textContent = '공유 링크 만드는 중... 🐾';
    btnShare.disabled = true;

    try {
      const { token } = await api(`/api/saju/dogs/${dog.id}/share/`, { method: 'POST', body: {} });
      // 링크 미리보기 썸네일: 백엔드가 고정 URL로 제공하는 오행별 공유 카드(1200×630, scripts/og 로 생성)
      const ogImageUrl = `${API_BASE_URL}/static/assets/og_${elementInfo(dog.main_element).slug}.jpg`;
      const tossLink = await getTossShareLink(`${APP_SCHEME}?share=${encodeURIComponent(token)}`, ogImageUrl);
      await share({ message: `${buildShareMessage()}\n\n${tossLink}` });
    } catch (error) {
      console.error(error);
      showToast(error instanceof ApiError
        ? (apiErrorMessage(error) || '공유 링크를 만들지 못했어요. 잠시 후 다시 시도해주세요.')
        : '공유하기는 토스 앱에서 사용할 수 있어요.');
    } finally {
      btnShare.textContent = originalText;
      btnShare.disabled = false;
    }
  });

  // 공유 링크로 들어온 경우: 친구의 공개 카드
  function renderSharedCard(card) {
    $('share-img').src = dogImageUrl(card.main_element);
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
      renderSharedCard(await api(`/api/saju/share/${encodeURIComponent(token)}/`));
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
  refreshMyDogs();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

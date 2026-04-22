import {
  getAnonymousKey,
  getTossShareLink,
  share,
  TossAds,
  loadFullScreenAd,
  showFullScreenAd,
} from '@apps-in-toss/web-framework';

document.addEventListener('DOMContentLoaded', async () => {
  // Screens
  const mainScreen = document.getElementById('main-screen');
  const inputScreen = document.getElementById('input-screen');
  const loadingScreen = document.getElementById('loading-screen');
  const resultScreen = document.getElementById('result-screen');

  // Buttons
  const btnGeneral = document.getElementById('btn-general');
  const btnChemistry = document.getElementById('btn-chemistry');
  const btnSubmit = document.getElementById('btn-submit');
  const btnShare = document.getElementById('btn-share');

  // Attendance Buttons
  const btnOpenAttendance = document.getElementById('btn-open-attendance');
  const attendanceModal = document.getElementById('attendance-modal');
  const btnCloseAttendance = document.getElementById('btn-close-attendance');
  const btnAttendanceStamp = document.getElementById('btn-attendance-stamp');
  const talismanModal = document.getElementById('talisman-modal');
  const btnCloseTalisman = document.getElementById('btn-close-talisman');
  const btnDownloadTalisman = document.getElementById('btn-download-talisman');
  const btnShareTalisman = document.getElementById('btn-share-talisman');
  const resultImage = document.getElementById('result-img');
  const tossAdContainer = document.getElementById('toss-ad-container');

  // Config
  const BASE_URL = 'https://web-production-285b5.up.railway.app';
  const MIN_LOADING_MS = 80;
  const TOSS_USER_KEY_STORAGE = 'daengsaju_user_key';
  const BANNER_AD_GROUP_ID = 'ait.v2.live.82786c3925d743b3';
  const FULLSCREEN_AD_GROUP_ID = window.__TOSS_FULLSCREEN_AD_GROUP_ID__ || 'ait.v2.live.3c235f3d3a424553';
  const SHARE_BUTTON_LABEL = '\uC6B4\uC138 \uACF5\uC720\uD558\uAE30';
  const SHARE_BUTTON_LOADING_LABEL = '\uACF5\uC720 \uB9C1\uD06C \uC900\uBE44 \uC911...';
  const SHARE_MESSAGE = '\uB315\uC0AC\uC8FC \uACB0\uACFC\uAC00 \uB3C4\uCC29\uD588\uC5B4\uC694.\n\uD1A0\uC2A4\uC5D0\uC11C \uBC14\uB85C \uD655\uC778\uD574\uBCF4\uC138\uC694.';
  const SHARE_ERROR_MESSAGE = '\uACF5\uC720 \uB9C1\uD06C\uB97C \uC900\uBE44\uD558\uC9C0 \uBABB\uD588\uC5B4\uC694. \uC7A0\uC2DC \uD6C4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574\uC8FC\uC138\uC694.';
  const FULLSCREEN_AD_FALLBACK_MESSAGE = '\uC804\uBA74 \uAD11\uACE0\uB97C \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD574 \uBC14\uB85C \uB0B4\uC6A9\uC744 \uC5F4\uC5B4\uB4DC\uB9B4\uAC8C\uC694.';

  const unlockedSections = {
    lifetime: false,
    chemistry: false,
  };
  let currentShareText = '\uB315\uB315\uC774\uB294 \uD0C0\uACE0\uB09C \uAE30\uC6B4\uC744 \uD655\uC778\uD574\uBCF4\uC138\uC694.';
  let currentShareImageUrl = `${BASE_URL}/assets/logo.png`;

  function resolveTossUserKey() {
    const params = new URLSearchParams(window.location.search);
    const candidates = [
      window.__TOSS_USER_KEY__,
      window.Toss?.userKey,
      window.Toss?.tossUserKey,
      params.get('toss_user_key'),
      params.get('tossUserKey'),
      params.get('userKey'),
      localStorage.getItem(TOSS_USER_KEY_STORAGE),
    ];
    const stableKey = candidates.find(value => typeof value === 'string' && value.trim());
    if (stableKey) {
      localStorage.setItem(TOSS_USER_KEY_STORAGE, stableKey);
      return stableKey;
    }
    return '';
  }

  let tossUserKey = resolveTossUserKey();

  if (btnShare) {
    btnShare.textContent = SHARE_BUTTON_LABEL;
  }

  try {
    const result = await getAnonymousKey();
    if (result?.type === 'HASH' && typeof result.hash === 'string') {
      tossUserKey = result.hash.trim();
      localStorage.setItem(TOSS_USER_KEY_STORAGE, tossUserKey);
    }
  } catch (error) {
    console.warn('[Toss] anonymous key unavailable:', error);
  }

  function requireUserKey() {
    tossUserKey = resolveTossUserKey();
    if (tossUserKey) return true;
    alert('토스 사용자 정보를 확인할 수 없어 다시 열어주세요.');
    return false;
  }

  function buildHeaders(includeJson = false) {
    const headers = {};
    if (includeJson) {
      headers['Content-Type'] = 'application/json';
    }
    if (tossUserKey) {
      headers['X-Toss-User-Key'] = tossUserKey;
    }
    return headers;
  }

  function apiUrl(path) {
    return `${BASE_URL}${path}`;
  }

  let isTossAdsReady = false;
  let tossBannerInstance = null;

  function mountTossBanner() {
    if (!isTossAdsReady || !tossAdContainer || tossBannerInstance) return;
    tossBannerInstance = TossAds.attachBanner(BANNER_AD_GROUP_ID, tossAdContainer, {
      variant: 'expanded',
      theme: 'dark',
      callbacks: {
        onAdFailedToRender: (payload) => console.warn('[Banner] failed:', payload),
        onNoFill: (payload) => console.warn('[Banner] no fill:', payload),
      },
    });
  }

  function unmountTossBanner() {
    if (!tossBannerInstance) return;
    tossBannerInstance.destroy();
    tossBannerInstance = null;
  }

  const bannerSupported =
    TossAds && typeof TossAds.initialize === 'function'
      ? (typeof TossAds.initialize.isSupported === 'function' ? TossAds.initialize.isSupported() : true)
      : false;

  if (bannerSupported) {
    TossAds.initialize({
      callbacks: {
        onInitialized: () => {
          isTossAdsReady = true;
          mountTossBanner();
        },
        onInitializationFailed: (error) => {
          console.warn('[TossAds] init failed:', error);
        },
      },
    });
  }

  // Attendance State
  let attendanceRecord = [];
  let currentStreak = 0;
  let currentTalismanDay = null;

  const TALISMAN_REWARDS = {
    3: { name: '초심자의 뼈다귀 부적', desc: '3일 연속 출석! 멍멍이의 에너지가 솟아납니다.' },
    7: { name: '행운의 댕댕 부적', desc: '럭키 7일! 이번 주 내내 기분 좋은 일이 가득할 거예요.' },
    10: { name: '재물운 명탐정 부적', desc: '10일 달성! 생각지도 못한 간식이나 행운이 찾아옵니다.' },
    15: { name: '대박 황금 부적', desc: '15일 달성! 주변에서 많은 복이 찾아오는 시기예요.' },
    20: { name: '전설의 댕댕 부적', desc: '당신은 진정한 댕사주 마스터!' },
  };
  const MILESTONES = [3, 7, 10, 15, 20];

  const todayDateObj = new Date();
  const currentMonth = todayDateObj.getMonth() + 1;
  const currentDaysInMonth = new Date(todayDateObj.getFullYear(), todayDateObj.getMonth() + 1, 0).getDate();
  const todayDate = todayDateObj.getDate();

  // Tab Logic
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      // Remove active class from all tabs
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      // Add active to clicked tab
      btn.classList.add('active');
      const targetTab = document.getElementById(btn.dataset.tab);
      targetTab.classList.add('active');

      // Reset scroll position to top when switching tabs
      const scrollContainer = document.querySelector('.result-scroll');
      if (scrollContainer) {
        scrollContainer.scrollTop = 0;
      }

      // Re-trigger reveal for the new tab
      revealCards();

      // Update Chart visually if changed to lifetime tab
      if (btn.dataset.tab === 'tab-lifetime') {
        animateBars();
      }
    });
  });

  // Input sections
  const inputTitle = document.getElementById('input-title');
  const ownerInputSection = document.getElementById('owner-input-section');
  const chemistryResultSection = document.getElementById('chemistry-result-section');
  const dogNameInput = document.getElementById('dog-name');
  const dogDateInput = document.getElementById('dog-date');
  const dogTimeInput = document.getElementById('dog-time');
  const dogLunarCheck = document.getElementById('dog-lunar');

  // State
  let testType = 'general'; // 'general' or 'chemistry'
  let radarChartInstance = null; // Store chart instance
  const externalScriptPromises = new Map();

  function loadExternalScript(src) {
    if (externalScriptPromises.has(src)) {
      return externalScriptPromises.get(src);
    }

    const promise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.crossOrigin = 'anonymous';
      script.onload = () => resolve(true);
      script.onerror = () => {
        externalScriptPromises.delete(src);
        reject(new Error(`Failed to load script: ${src}`));
      };
      document.head.appendChild(script);
    });

    externalScriptPromises.set(src, promise);
    return promise;
  }

  async function ensureChartJs() {
    if (window.Chart) return true;
    try {
      await loadExternalScript('https://cdn.jsdelivr.net/npm/chart.js');
      return true;
    } catch (error) {
      console.warn('[External] Chart.js 로드 실패:', error);
      return false;
    }
  }

  async function ensureHtml2Canvas() {
    if (window.html2canvas) return true;
    try {
      await loadExternalScript('https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js');
      return true;
    } catch (error) {
      console.warn('[External] html2canvas 로드 실패:', error);
      return false;
    }
  }

  async function ensureConfetti() {
    if (typeof window.confetti === 'function') return true;
    try {
      await loadExternalScript('https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js');
      return true;
    } catch (error) {
      console.warn('[External] confetti 로드 실패:', error);
      return false;
    }
  }

  function resetChemistryResult() {
    document.getElementById('res-chem-score').textContent = '--';
    document.getElementById('res-chem-title').textContent = '';
    document.getElementById('res-chem-owner-element').textContent = '(-)';
    document.getElementById('res-chem-dog-element').textContent = '(-)';
    document.getElementById('res-chem-rel').textContent = '';
    document.getElementById('res-chem-desc').innerHTML = '';
    document.getElementById('res-chem-advice').innerHTML = '';
    document.getElementById('res-chem-advice').style.display = 'none';
  }

  function renderAnalysisResult(basicData, perData, luckData, dogName) {
    const elementMap = { '목': 'wood', '화': 'fire', '토': 'earth', '금': 'metal', '수': 'water' };
    const elementColorMap = { '목': 'text-wood', '화': 'text-fire', '토': 'text-earth', '금': 'text-metal', '수': 'text-water' };
    const elementHanjaMap = { '목': '木', '화': '火', '토': '土', '금': '金', '수': '水' };

    updateSajuTable(basicData);

    const imgName = elementMap[basicData.main_element] || 'fire';
    const colorClass = elementColorMap[basicData.main_element] || 'text-fire';
    const hanjaEl = elementHanjaMap[basicData.main_element] || '火';

    if (resultImage) {
      resultImage.src = `/assets/${imgName}_dog.png`;
    } else {
      document.querySelector('.result-img').src = `/assets/${imgName}_dog.png`;
    }
    currentShareImageUrl = `${BASE_URL}/assets/${imgName}_dog.png`;
    currentShareText = `${dogName}? ${basicData.main_element}(${hanjaEl})? ??? ?????.`;
    document.getElementById('res-summary').innerHTML = `${formatText(perData.personality_summary)}<br><span class="${colorClass}">${basicData.main_element}(${hanjaEl})</span>? ??? ??? <span class="dog-name-display">${dogName}</span>!`;
    document.getElementById('res-food').innerHTML = formatText(perData.treat_luck);
    document.getElementById('res-energy').innerHTML = formatText(perData.vitality_analysis);
    document.getElementById('res-love').innerHTML = formatText(perData.care_tips);
    document.getElementById('res-social').innerHTML = formatText(perData.social_analysis);

    document.getElementById('res-luck-score').textContent = luckData.luck_score;
    document.getElementById('res-luck-msg').innerHTML = formatText(luckData.message);
    document.getElementById('res-luck-color').textContent = luckData.lucky_color;
    document.getElementById('res-luck-dir').textContent = luckData.lucky_direction;
  }

  async function fetchAnalysisBundle(dogId) {
    const response = await fetch(apiUrl(`/api/saju/dogs/${dogId}/analysis/`), { headers: buildHeaders() });
    if (!response.ok) {
      throw new Error('통합 분석 로드 실패');
    }

    return response.json();
  }

  async function fetchAnalysisWithFallback(dogId) {
    try {
      const bundleData = await fetchAnalysisBundle(dogId);
      return {
        basicData: bundleData.basics,
        perData: bundleData.personality,
        luckData: bundleData.daily_luck,
      };
    } catch (bundleError) {
      console.warn('[Analysis] 통합 API fallback:', bundleError);

      const basicRes = await fetch(apiUrl(`/api/saju/dogs/${dogId}/basics/`), { headers: buildHeaders() });
      if (!basicRes.ok) throw new Error('기본정보 로드 실패');
      const basicData = await basicRes.json();

      const [perRes, luckRes] = await Promise.all([
        fetch(apiUrl(`/api/saju/dogs/${dogId}/personality/`), { headers: buildHeaders() }),
        fetch(apiUrl(`/api/saju/dogs/${dogId}/daily-luck/`), { headers: buildHeaders() }),
      ]);

      if (!perRes.ok) throw new Error('성격 분석 로드 실패');
      if (!luckRes.ok) throw new Error('오늘 운세 로드 실패');

      const [perData, luckData] = await Promise.all([perRes.json(), luckRes.json()]);
      return { basicData, perData, luckData };
    }
  }

  function getCaptureScale(targetElement) {
    const maxDimension = Math.max(targetElement.scrollWidth || 0, targetElement.scrollHeight || 0);
    if (maxDimension > 2200) return 1.2;
    if (maxDimension > 1600) return 1.4;
    return Math.min(window.devicePixelRatio || 1, 1.5);
  }

  function releaseCanvasResources(canvas, imageElement = null) {
    if (canvas) {
      canvas.width = 0;
      canvas.height = 0;
    }
    if (imageElement) {
      imageElement.removeAttribute('src');
    }
  }

  function updateAttendanceStampButton() {
    if (!btnAttendanceStamp) return;
    const stampedToday = attendanceRecord.includes(todayDate);
    btnAttendanceStamp.disabled = stampedToday;
    btnAttendanceStamp.textContent = stampedToday ? '오늘 출석 완료' : '오늘 출석하기';
    btnAttendanceStamp.style.opacity = stampedToday ? '0.6' : '1';
  }

  const screens = Array.from(document.querySelectorAll('.screen'));

  function showScreen(screenElement) {
    screens.forEach(screen => {
      const isActive = screen === screenElement;
      screen.classList.toggle('active', isActive);
      screen.style.display = isActive ? 'flex' : 'none';
    });
  }

  function createUnlockOverlay(sectionKey) {
    const overlay = document.createElement('div');
    overlay.className = 'dynamic-unlock-overlay';
    overlay.style.cssText = [
      'position:absolute',
      'inset:0',
      'display:flex',
      'flex-direction:column',
      'justify-content:center',
      'align-items:center',
      'gap:10px',
      'padding:20px',
      'border-radius:18px',
      'background:linear-gradient(180deg, rgba(11,17,33,0.55), rgba(11,17,33,0.92))',
      'backdrop-filter:blur(8px)',
      '-webkit-backdrop-filter:blur(8px)',
      'z-index:2',
      'text-align:center',
    ].join(';');

    const badge = document.createElement('div');
    badge.textContent = '\uC7A0\uAE08 \uCF58\uD150\uCE20';
    badge.style.cssText = [
      'font-size:12px',
      'font-weight:700',
      'letter-spacing:0.02em',
      'color:#F8FAFC',
      'padding:6px 10px',
      'border-radius:999px',
      'background:rgba(255,255,255,0.12)',
      'border:1px solid rgba(255,255,255,0.16)',
    ].join(';');

    const title = document.createElement('p');
    title.textContent =
      sectionKey === 'chemistry'
        ? '\uC804\uBA74 \uAD11\uACE0\uB97C \uBCF4\uACE0 \uAD81\uD569 \uD574\uC11D \uC804\uCCB4\uB97C \uC5F4\uC5B4\uBCF4\uC138\uC694.'
        : '\uC804\uBA74 \uAD11\uACE0\uB97C \uBCF4\uACE0 \uD3C9\uC0DD \uC0AC\uC8FC \uD574\uC11D \uC804\uCCB4\uB97C \uC5F4\uC5B4\uBCF4\uC138\uC694.';
    title.style.cssText = 'margin:0;color:#FFFFFF;font-size:15px;font-weight:700;line-height:1.5;';

    const sub = document.createElement('p');
    sub.textContent = '\uAD11\uACE0 \uC2DC\uCCAD \uD6C4 \uBC14\uB85C \uC774\uC5B4\uC11C \uB0B4\uC6A9\uC744 \uD655\uC778\uD560 \uC218 \uC788\uC5B4\uC694.';
    sub.style.cssText = 'margin:0;color:rgba(255,255,255,0.82);font-size:13px;line-height:1.45;';

    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = '\uC804\uBA74 \uAD11\uACE0 \uBCF4\uACE0 \uC5F4\uAE30';
    button.style.cssText = [
      'margin-top:6px',
      'width:100%',
      'max-width:220px',
      'height:46px',
      'border:none',
      'border-radius:14px',
      'background:linear-gradient(135deg, #8B5CF6, #3B82F6)',
      'color:#fff',
      'font-size:14px',
      'font-weight:800',
      'cursor:pointer',
      'box-shadow:0 10px 26px rgba(59,130,246,0.26)',
    ].join(';');
    button.addEventListener('click', () => requestSectionUnlock(sectionKey, button));

    overlay.appendChild(badge);
    overlay.appendChild(title);
    overlay.appendChild(sub);
    overlay.appendChild(button);
    return overlay;
  }

  function ensureLockShell(target, sectionKey) {
    if (!target) return null;

    let shell = target.parentElement;
    if (!shell || !shell.classList.contains('dynamic-lock-shell')) {
      shell = document.createElement('div');
      shell.className = 'dynamic-lock-shell';
      shell.style.position = 'relative';
      shell.style.width = '100%';
      target.parentNode.insertBefore(shell, target);
      shell.appendChild(target);
    }

    target.style.transition = 'filter 0.25s ease, opacity 0.25s ease';
    target.style.willChange = 'filter, opacity';

    let overlay = shell.querySelector('.dynamic-unlock-overlay');
    if (!overlay) {
      overlay = createUnlockOverlay(sectionKey);
      shell.appendChild(overlay);
    }

    return { shell, overlay };
  }

  function setLocked(target, sectionKey, locked) {
    const shellParts = ensureLockShell(target, sectionKey);
    if (!shellParts) return;

    target.style.filter = locked ? 'blur(7px)' : 'none';
    target.style.opacity = locked ? '0.3' : '1';
    target.style.pointerEvents = locked ? 'none' : 'auto';
    shellParts.overlay.style.display = locked ? 'flex' : 'none';
  }

  function applyContentLocks() {
    const lifetimeTargets = ['res-food', 'res-energy', 'res-love', 'res-social']
      .map(id => document.getElementById(id))
      .filter(Boolean)
      .map(el => el.closest('.detail-content') || el);

    lifetimeTargets.forEach(target => setLocked(target, 'lifetime', !unlockedSections.lifetime));

    const chemDesc = document.getElementById('res-chem-desc');
    const chemAdvice = document.getElementById('res-chem-advice');
    const shouldLockChemistry = testType === 'chemistry' && !unlockedSections.chemistry;

    if (chemDesc) {
      setLocked(chemDesc, 'chemistry', shouldLockChemistry);
    }
    if (chemAdvice && chemAdvice.style.display !== 'none') {
      setLocked(chemAdvice, 'chemistry', shouldLockChemistry);
    }
  }

  async function openFullScreenAd() {
    const canLoad =
      typeof loadFullScreenAd === 'function' &&
      (typeof loadFullScreenAd.isSupported !== 'function' || loadFullScreenAd.isSupported());
    const canShow =
      typeof showFullScreenAd === 'function' &&
      (typeof showFullScreenAd.isSupported !== 'function' || showFullScreenAd.isSupported());

    if (!FULLSCREEN_AD_GROUP_ID) {
      console.warn('[FullscreenAd] missing ad group id');
      return false;
    }

    if (!canLoad || !canShow) {
      console.warn('[FullscreenAd] not supported in this environment');
      return false;
    }

    await new Promise((resolve, reject) => {
      loadFullScreenAd({
        options: { adGroupId: FULLSCREEN_AD_GROUP_ID },
        onEvent: (event) => {
          if (event?.type === 'loaded') {
            resolve(true);
          }
        },
        onError: reject,
      });
    });

    return new Promise((resolve, reject) => {
      showFullScreenAd({
        options: { adGroupId: FULLSCREEN_AD_GROUP_ID },
        onEvent: (event) => {
          if (!event) return;
          if (event.type === 'dismissed' || event.type === 'userEarnedReward') {
            resolve(true);
          }
          if (event.type === 'failedToShow') {
            resolve(false);
          }
        },
        onError: reject,
      });
    });
  }

  async function requestSectionUnlock(sectionKey, triggerButton) {
    const originalLabel = triggerButton.textContent;
    triggerButton.disabled = true;
    triggerButton.textContent = '\uAD11\uACE0 \uC900\uBE44 \uC911...';

    try {
      const didComplete = await openFullScreenAd();
      if (!didComplete) {
        alert(FULLSCREEN_AD_FALLBACK_MESSAGE);
      }
      unlockedSections[sectionKey] = true;
      applyContentLocks();
    } catch (error) {
      console.warn('[FullscreenAd] unlock fallback:', error);
      alert(FULLSCREEN_AD_FALLBACK_MESSAGE);
      unlockedSections[sectionKey] = true;
      applyContentLocks();
    } finally {
      triggerButton.disabled = false;
      triggerButton.textContent = originalLabel;
    }
  }

  // Initialize screen state without owning the root history entry.
  showScreen(mainScreen);
  mountTossBanner();

  window.addEventListener('popstate', (e) => {
    if (e.state && e.state.screenId) {
      const screen = document.getElementById(e.state.screenId);
      if (screen) {
        navigateTo(screen, false);
      }
    } else {
      navigateTo(mainScreen, false);
    }
  });

  // Navigation logic
  function navigateTo(screenElement, pushHistory = true) {
    showScreen(screenElement);

    if (pushHistory && screenElement.id !== 'main-screen') {
      history.pushState({ screenId: screenElement.id }, '', `#${screenElement.id}`);
    }

    if (screenElement === mainScreen) {
      mountTossBanner();
    } else {
      unmountTossBanner();
    }

    // reset scroll to top
    if (screenElement === resultScreen) {
      document.querySelector('.result-scroll').scrollTop = 0;

      const tabNav = document.querySelector('.tab-nav');
      const tabToday = document.getElementById('tab-today');
      const tabLifetime = document.getElementById('tab-lifetime');
      const chemSection = document.getElementById('chemistry-result-section');

      if (testType === 'chemistry') {
        // 댕궁합 단독 모드
        if (tabNav) tabNav.style.display = 'none';
        if (tabToday) tabToday.style.display = 'none';
        if (tabLifetime) tabLifetime.style.display = 'none';
        if (chemSection) chemSection.style.display = 'block';
      } else {
        // 일반 댕사주 모드: 탭 UI 복원
        if (tabNav) tabNav.style.display = 'flex';
        if (tabToday) tabToday.style.display = 'block';
        if (tabLifetime) tabLifetime.style.display = 'block';
        if (chemSection) chemSection.style.display = 'none';
        // Default to first tab
        if (tabBtns && tabBtns.length > 0) {
          tabBtns[0].click();
        }
        // Staggered Reveal Cards
        revealCards();
      }

      applyContentLocks();
    }
  }

  function revealCards() {
    const cards = document.querySelectorAll('.tab-content.active .fade-in, #chemistry-result-section.fade-in');
    cards.forEach(c => c.classList.remove('reveal'));

    requestAnimationFrame(() => {
      cards.forEach(card => card.classList.add('reveal'));
    });
  }

  // Event Listeners
  btnGeneral.addEventListener('click', () => {
    testType = 'general';
    inputTitle.innerHTML = '우리아이의 타고난<br>기질을 알아볼까요?';
    ownerInputSection.classList.add('hidden');
    navigateTo(inputScreen);
  });

btnChemistry.addEventListener('click', () => {
  testType = 'chemistry';
  inputTitle.innerHTML = '보호자와 댕댕이의<br>상생 궁합은?';
  ownerInputSection.classList.remove('hidden');
  navigateTo(inputScreen);
});


btnChemistry.addEventListener('click', resetChemistryResult);

btnSubmit.addEventListener('click', async (e) => {
  e.preventDefault();
  if (!requireUserKey()) {
    return;
  }
  if (!dogNameInput.value || !dogDateInput.value) {
    alert("강아지 이름과 생년월일을 정확히 입력해주세요!");
    return;
  }

  if (testType === 'chemistry' && !document.getElementById('owner-date').value) {
    alert("보호자 생년월일을 입력해주세요!");
    return;
  }

  const dogName = dogNameInput.value.trim();
  unlockedSections.lifetime = false;
  unlockedSections.chemistry = false;
  document.querySelectorAll('.dog-name-display').forEach(el => el.textContent = dogName);

  if (testType === 'chemistry') {
    chemistryResultSection.style.display = 'block';
  } else {
    chemistryResultSection.style.display = 'none';
  }

  navigateTo(loadingScreen, false);

  // UX: Labor Illusion (신뢰감을 주기 위한 페이크 로딩 2초)
  await new Promise(resolve => setTimeout(resolve, MIN_LOADING_MS));

  try {
    // 1. 등록 (POST /api/saju/dogs/)
    const dogGender = document.querySelector('input[name="dog-gender"]:checked').value;
    const postData = {
      social_id: tossUserKey,
      nickname: "데모유저",
      dog: {
        name: dogName,
        birth_date: dogDateInput.value,
        birth_time: dogTimeInput.value || null,
        is_lunar: dogLunarCheck.checked,
        gender: dogGender === 'M' ? 'MALE' : 'FEMALE',
        is_estimated_birth: false
      }
    };

    const regRes = await fetch(apiUrl('/api/saju/dogs/'), {
      method: 'POST',
      headers: buildHeaders(true),
      body: JSON.stringify(postData)
    });
    const regData = await regRes.json();
    if (!regRes.ok) {
      console.error("등록 서버 에러:", regData);
      throw new Error("등록 실패: " + (regData.error || JSON.stringify(regData)));
    }

    const dogId = regData.dog_id;
    console.log("[Analysis] 등록 성공, ID:", dogId);

    const analysisPromise = fetchAnalysisWithFallback(dogId);

    // 5. 댕궁합 분석 (testType이 chemistry일 때만 호출)
    let chemistryPromise = null;
    if (testType === 'chemistry') {
      const ownerDate = document.getElementById('owner-date').value;
      const ownerTime = document.getElementById('owner-time').value;
      chemistryPromise = fetch(apiUrl(`/api/saju/dogs/${dogId}/compatibility/`), {
        method: 'POST',
        headers: buildHeaders(true),
        body: JSON.stringify({
          owner_birth_date: ownerDate,
          owner_birth_time: ownerTime
        })
      });
    }

    const { basicData, perData, luckData } = await analysisPromise;
    renderAnalysisResult(basicData, perData, luckData, dogName);
    applyContentLocks();

    if (chemistryPromise) {
      try {
        const chemRes = await chemistryPromise;
        const chemData = await chemRes.json();

        if (chemRes.ok) {
          document.getElementById('res-chem-score').textContent = chemData.score || '--';
          document.getElementById('res-chem-title').textContent = chemData.title || '';
          document.getElementById('res-chem-owner-element').textContent = `(${chemData.owner_element})`;
          document.getElementById('res-chem-dog-element').textContent = `(${chemData.dog_element})`;
          document.getElementById('res-chem-rel').textContent = `✨ ${chemData.relationship_type} 관계 ✨`;
          document.getElementById('res-chem-desc').innerHTML = formatText(chemData.description || '');

          if (chemData.advice) {
            document.getElementById('res-chem-advice').innerHTML = `<strong>💡 어드바이스:</strong><br>${formatText(chemData.advice)}`;
            document.getElementById('res-chem-advice').style.display = 'block';
          } else {
            document.getElementById('res-chem-advice').style.display = 'none';
          }

          chemistryResultSection.style.display = 'block';
          applyContentLocks();
        }
      } catch (err) {
        console.error("궁합 조회 실패:", err);
      }
    }

    navigateTo(resultScreen, true);
    // 오행 바 그래프 업데이트 및 애니메이션
    await updateGraphs(basicData.element_distribution);

    // Tab 1 is default, animation happens on tab click, but we can call it once just in case
    // animateBars();

  } catch (error) {
    console.error(error);
    alert("운세를 분석하는 중 오류가 발생했습니다. 확인 후 다시 시도해주세요.");
    navigateTo(inputScreen, false);
  }
});

btnShare.addEventListener('click', async () => {
  const originalText = SHARE_BUTTON_LABEL;
  btnShare.textContent = SHARE_BUTTON_LOADING_LABEL;
  btnShare.disabled = true;

  try {
    const shareLink = await getTossShareLink('intoss://daengsaju', currentShareImageUrl);
    await share({
      message: `${currentShareText}
${shareLink}`,
    });
  } catch (e) {
    console.error(e);
    alert(SHARE_ERROR_MESSAGE);
  } finally {
    btnShare.textContent = originalText;
    btnShare.disabled = false;
  }
});

// 사주 표 파싱 함수
function updateSajuTable(data) {
  const splitChar = (str) => {
    if (!str || str === '알수없음') return ['-', '-'];
    return [str.charAt(0) || '-', str.charAt(1) || '-'];
  };

  const y = splitChar(data.year_pillar);
  const m = splitChar(data.month_pillar);
  const d = splitChar(data.day_pillar);
  const h = splitChar(data.hour_pillar || '--');

  document.getElementById('stem-year').innerHTML = `<span class="hanja">年</span><br>${y[0]}`;
  document.getElementById('stem-month').innerHTML = `<span class="hanja">月</span><br>${m[0]}`;
  document.getElementById('stem-day').innerHTML = `<span class="hanja">日</span><br>${d[0]}`;
  document.getElementById('stem-hour').innerHTML = `<span class="hanja">時</span><br>${h[0]}`;

  document.getElementById('branch-year').innerHTML = `<span class="hanja">年</span><br>${y[1]}`;
  document.getElementById('branch-month').innerHTML = `<span class="hanja">月</span><br>${m[1]}`;
  document.getElementById('branch-day').innerHTML = `<span class="hanja">日</span><br>${d[1]}`;
  document.getElementById('branch-hour').innerHTML = `<span class="hanja">時</span><br>${h[1]}`;
}

// Draw or Update Chart.js Radar and set bar variables
async function updateGraphs(dist) {
  const chartReady = await ensureChartJs();
  const woods = dist['목'] || 0;
  const fires = dist['화'] || 0;
  const earths = dist['토'] || 0;
  const metals = dist['금'] || 0;
  const waters = dist['수'] || 0;

  document.getElementById('val-wood').textContent = woods + '%';
  document.getElementById('val-fire').textContent = fires + '%';
  document.getElementById('val-earth').textContent = earths + '%';
  document.getElementById('val-metal').textContent = metals + '%';
  document.getElementById('val-water').textContent = waters + '%';

  document.getElementById('bar-wood').dataset.targetWidth = woods + '%';
  document.getElementById('bar-fire').dataset.targetWidth = fires + '%';
  document.getElementById('bar-earth').dataset.targetWidth = earths + '%';
  document.getElementById('bar-metal').dataset.targetWidth = metals + '%';
  document.getElementById('bar-water').dataset.targetWidth = waters + '%';

  if (!chartReady || typeof window.Chart !== 'function') {
    animateBars();
    return;
  }

  // Chart.js Radar
  const ctx = document.getElementById('radarChart').getContext('2d');

  const dataValues = [woods, fires, earths, metals, waters];

  if (radarChartInstance) {
    radarChartInstance.data.datasets[0].data = dataValues;
    radarChartInstance.update();
  } else {
    radarChartInstance = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: ['목(木)', '화(火)', '토(土)', '금(金)', '수(水)'],
        datasets: [{
          label: '기질 밸런스',
          data: dataValues,
          backgroundColor: 'rgba(49, 130, 246, 0.15)',
          borderColor: 'rgba(49, 130, 246, 0.8)',
          pointBackgroundColor: '#fff',
          pointBorderColor: 'rgba(49, 130, 246, 1)',
          pointHoverBackgroundColor: 'rgba(49, 130, 246, 1)',
          borderWidth: 3,
          pointRadius: 5,
          pointHoverRadius: 7
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            pointLabels: {
              font: { family: 'Pretendard', size: 13, weight: '700' },
              color: '#FFFFFF'
            },
            ticks: { display: false, min: 0 }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return context.raw + '%';
              }
            }
          }
        }
      }
    });
  }
}

function animateBars() {
  const bars = document.querySelectorAll('.bar-fill');
  bars.forEach(bar => {
    bar.style.transition = 'none'; // reset transition
    bar.style.width = '0%';
  });
  // Add small delay to let DOM repaint
  setTimeout(() => {
    bars.forEach(bar => {
      bar.style.transition = 'width 1.2s cubic-bezier(0.25, 1, 0.5, 1)';
      bar.style.width = bar.dataset.targetWidth || '0%';
    });
  }, 50);
}

// 텍스트 포맷팅 함수 (개행 처리 및 **강조** 지원)
function formatText(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.*?)\*\*/g, '<span class="highlight-text">$1</span>') // **강조** 처리
    .replace(/\n/g, '<br>'); // 개행 처리
}

// ─── Attendance Logic ───────────────────────────────────────────
async function loadAttendance() {
  if (!requireUserKey()) {
    throw new Error('Missing toss user key');
  }
  try {
    const res = await fetch(`${BASE_URL}/api/saju/attendance/`, {
      headers: buildHeaders()
    });
    if (!res.ok) throw new Error('출석 조회 실패');
    const data = await res.json();
    attendanceRecord = data.attended_days || [];
    currentStreak = data.streak_count || 0;
    updateAttendanceStampButton();
    return data;
  } catch (e) {
    console.warn('[Attendance] API 실패:', e);
    throw e;
  }
}

function renderCalendar() {
  const grid = document.getElementById('calendar-grid');
  if (!grid) return;
  grid.innerHTML = '';

  const totalAttended = attendanceRecord.length;
  document.getElementById('calendar-streak').textContent = totalAttended + '일';

  const nextRewardDay = MILESTONES.find(m => m > totalAttended) || 20;
  const daysLeft = Math.max(0, nextRewardDay - totalAttended);
  const progressPercent = Math.min((totalAttended / nextRewardDay) * 100, 100);

  document.getElementById('calendar-progress-text').textContent = `다음 스페셜 부적까지 단 ${daysLeft}일 남았어요!`;
  document.getElementById('calendar-progress-fill').style.width = progressPercent + '%';

  for (let day = 1; day <= currentDaysInMonth; day++) {
    const isStamped = attendanceRecord.includes(day);
    const isToday = day === todayDate;

    const cell = document.createElement('div');
    cell.className = 'calendar-cell';
    if (isStamped) cell.classList.add('stamped');
    if (isToday && !isStamped) cell.classList.add('today-pending');

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

    grid.appendChild(cell);
  }
  updateAttendanceStampButton();
}

async function handleStamp() {
  if (!requireUserKey()) return;
  if (attendanceRecord.includes(todayDate)) return;

  try {
    const res = await fetch(`${BASE_URL}/api/saju/attendance/`, {
      method: 'POST',
      headers: buildHeaders(true),
      body: JSON.stringify({ social_id: tossUserKey })
    });
    if (!res.ok) throw new Error('출석 저장 실패');
    const data = await res.json();

    if (!data.stamped) {
      attendanceRecord = data.attended_days || attendanceRecord;
      currentStreak = data.streak_count || currentStreak;
      renderCalendar();
      return;
    }

    attendanceRecord = data.attended_days || [];
    currentStreak = data.streak_count || 0;

    renderCalendar();

    const confettiReady = await ensureConfetti();
    if (confettiReady && typeof confetti === 'function') {
      confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, colors: ['#FF69B4', '#FFD700', '#ffffff'] });
    }

    if (data.new_milestone) {
      setTimeout(() => { showTalisman(data.new_milestone); }, 1000);
    }
  } catch (e) {
    console.warn('[Attendance] POST 실패:', e);
    alert('출석 처리 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.');
  }
}

function showTalisman(streak) {
  currentTalismanDay = streak;
  const reward = TALISMAN_REWARDS[streak];
  document.getElementById('talisman-name').textContent = reward.name;
  document.getElementById('talisman-desc').textContent = reward.desc;
  const imgEl = document.getElementById('talisman-img');
  imgEl.src = `/assets/talisman_${streak}.png`;
  imgEl.onerror = () => { imgEl.style.display = 'none'; };
  imgEl.style.display = 'block';

  talismanModal.classList.remove('hidden');
}

if (btnOpenAttendance) {
  btnOpenAttendance.addEventListener('click', async () => {
    try {
      await loadAttendance();
      renderCalendar();
      attendanceModal.classList.remove('hidden');
    } catch (error) {
      console.error(error);
    }
  });
}
if (btnAttendanceStamp) {
  btnAttendanceStamp.addEventListener('click', handleStamp);
}
if (btnCloseAttendance) {
  btnCloseAttendance.addEventListener('click', () => {
    attendanceModal.classList.add('hidden');
  });
}
if (btnCloseTalisman) {
  btnCloseTalisman.addEventListener('click', () => {
    talismanModal.classList.add('hidden');
  });
}
if (btnDownloadTalisman) {
  btnDownloadTalisman.addEventListener('click', async () => {
    const origText = btnDownloadTalisman.innerHTML;
    btnDownloadTalisman.innerHTML = "저장 중...";
    try {
      const html2CanvasReady = await ensureHtml2Canvas();
      if (!html2CanvasReady || typeof window.html2canvas !== 'function') {
        alert('이미지 저장 기능을 불러오지 못했어요. 잠시 후 다시 시도해주세요.');
        return;
      }
      const wrapper = document.getElementById('talisman-content-wrapper');
      const canvas = await html2canvas(wrapper, {
        backgroundColor: '#1E1E2A',
        useCORS: true,
        scale: getCaptureScale(wrapper)
      });
      let dataUrl = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = `daengsaju_talisman_${currentStreak}.png`;
      a.click();
      dataUrl = null;
      releaseCanvasResources(canvas);
    } catch (e) {
      console.error(e);
      alert('이미지 저장에 실패했습니다.');
    }
    btnDownloadTalisman.innerHTML = origText;
  });
}
if (btnShareTalisman) {
  btnShareTalisman.addEventListener('click', async () => {
    if (navigator.share) {
      try {
        const reward = TALISMAN_REWARDS[currentTalismanDay];
        await navigator.share({
          title: '댕사주 스페셜 부적',
          text: `댕사주에서 ${currentStreak}일 출석하고 '${reward.name}'을 획득했어요! 🐾`,
          url: window.location.href,
        });
      } catch (e) {
        console.log('Share canceled or failed', e);
      }
    } else {
      alert('지원하지 않는 브라우저입니다.');
    }
  });
}
});

import { getAnonymousKey, share, getTossShareLink, TossAds, loadFullScreenAd, showFullScreenAd } from '@apps-in-toss/web-framework';

const BASE_URL = 'https://web-production-285b5.up.railway.app';

document.addEventListener('DOMContentLoaded', async () => {
  // Get User Key from Toss Bridge
  let tossUserKey = null;
  try {
    const result = await getAnonymousKey();
    if (result && result.type === 'HASH') {
      tossUserKey = result.hash;
    }
  } catch (e) {
    console.warn("Toss Bridge not available or failed to get user key", e);
  }

  function getUserKey() {
    return typeof tossUserKey === 'string' ? tossUserKey.trim() : '';
  }

  function requireUserKey() {
    const userKey = getUserKey();
    if (userKey) return userKey;
    alert('Toss user key is unavailable. Please reopen this app from Toss.');
    return '';
  }

  function buildHeaders(includeJson = false) {
    const headers = {};
    const userKey = getUserKey();

    if (includeJson) {
      headers['Content-Type'] = 'application/json';
    }

    if (userKey) {
      headers['X-Toss-User-Key'] = userKey;
    }

    return headers;
  }

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

  // Initialize History state
  // Don't inject #main-screen on the URL initially. Leave it empty so the native back stack
  // knows this is the root of the app, and triggers the standard exit prompt when backed out.

  window.addEventListener('popstate', () => {
    // If the hash is empty, it means we are at the root (main screen)
    const hash = location.hash.replace('#', '') || 'main-screen';
    const screen = document.getElementById(hash);
    if (screen) {
      showScreen(screen);
    } else {
      showScreen(mainScreen);
    }
  });

  // Navigation logic
  function navigateTo(screenElement, pushHistory = true) {
    showScreen(screenElement);

    if (pushHistory) {
      const targetHash = screenElement.id === 'main-screen' ? '' : `#${screenElement.id}`;
      // Use pushState to avoid auto-scrolling to the anchor ID
      if (location.hash !== targetHash && (location.hash || targetHash !== '')) {
        history.pushState(null, '', targetHash || window.location.pathname);
      }
    }
  }

  function showScreen(screenElement) {
    document.querySelectorAll('.screen').forEach(s => {
      s.classList.remove('active');
      setTimeout(() => {
        if (!s.classList.contains('active')) {
          s.style.display = 'none';
        }
      }, 350); // wait for fade out explicitly to release memory layout frame
    });

    screenElement.style.display = 'flex';
    // requestAnimationFrame을 두 번 중첩하여 브라우저의 레이아웃 병목(렉)을 줄이고 부드럽게 페이드인
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        screenElement.classList.add('active');

        // 메모리/렌더링 최적화: 결과 화면은 배경 불투명(bg-gray)이므로 무거운 배경 애니메이션 전체 숨김처리
        const bgBlobs = document.querySelector('.bg-blobs');
        if (bgBlobs) {
          if (screenElement.id === 'result-screen') {
            bgBlobs.style.display = 'none';
          } else {
            bgBlobs.style.display = 'block';
          }
        }

        // 메인화면일 때만 배너 마운트 (active 추가 직후 실행 보장)
        if (screenElement.id === 'main-screen') {
          if (typeof mountTossBanner === 'function') mountTossBanner();
        } else {
          if (typeof unmountTossBanner === 'function') unmountTossBanner();
        }
      });
    });

    // reset scroll to top
    if (screenElement === resultScreen) {
      const scrollContainer = document.querySelector('.result-scroll');
      if (scrollContainer) scrollContainer.scrollTop = 0;

      const tabNav = document.querySelector('.tab-nav');
      const tabToday = document.getElementById('tab-today');
      const tabLifetime = document.getElementById('tab-lifetime');
      const chemSection = document.getElementById('chemistry-result-section');

      // Re-lock the report on every new result
      lockReports();
      lockChemReport();

      if (testType === 'chemistry') {
        // 댕궁합 단독 모드
        if (tabNav) tabNav.style.display = 'none';
        if (tabToday) tabToday.style.display = 'none';
        if (tabLifetime) tabLifetime.style.display = 'none';
        if (chemSection) chemSection.style.display = 'block';
      } else {
        // 일반 댕사주 모드: 탭 UI 복원
        if (tabNav) tabNav.style.display = 'flex';
        if (tabToday) tabToday.style.display = '';
        if (tabLifetime) tabLifetime.style.display = '';
        if (chemSection) chemSection.style.display = 'none';
        // Default to first tab
        if (tabBtns && tabBtns.length > 0) {
          tabBtns[0].click();
        }
        // Staggered Reveal Cards
        revealCards();
      }
    }
  }

  // Initial render
  setTimeout(() => {
    const initialHash = location.hash.replace('#', '') || 'main-screen';
    const initialScreen = document.getElementById(initialHash);
    if (initialScreen) {
      showScreen(initialScreen);
    }
  }, 0);

  // Initialize TossAds Banner
  let isTossAdsReady = false;
  let tossBannerInstance = null;

  function mountTossBanner() {
    if (!isTossAdsReady) return;
    const adContainer = document.getElementById('toss-ad-container');
    if (!adContainer) return;

    if (tossBannerInstance) {
      tossBannerInstance.destroy();
      tossBannerInstance = null;
    }
    tossBannerInstance = TossAds.attachBanner('ait.v2.live.82786c3925d743b3', adContainer, {
      variant: 'expanded',
      theme: 'dark',
      callbacks: {
        onAdFailedToRender: (p) => console.error('[Banner] failed', p),
        onNoFill: (p) => console.warn('[Banner] no fill', p),
      }
    });
  }

  function unmountTossBanner() {
    if (tossBannerInstance) {
      tossBannerInstance.destroy();
      tossBannerInstance = null;
    }
  }

  const bannerSupported = TossAds && typeof TossAds.initialize === 'function'
    ? (typeof TossAds.initialize.isSupported === 'function' ? TossAds.initialize.isSupported() : true)
    : false;

  console.log('[TossAds] banner supported:', bannerSupported);

  if (bannerSupported) {
    TossAds.initialize({
      callbacks: {
        onInitialized: () => {
          console.log('[TossAds] initialized OK');
          isTossAdsReady = true;
          // 앱 시작 시 메인화면에 바로 배너 부착 (타이밍 문제 없이 항상 호출)
          mountTossBanner();
        },
        onInitializationFailed: (err) => console.error('[TossAds] init failed', err)
      }
    });
  }

  // ─── Interstitial (전면) 광고 관리 ───────────────────────────────────────
  const INTERSTITIAL_AD_ID = 'ait.v2.live.3c235f3d3a424553';
  let interstitialAdLoaded = false;
  let interstitialUnregister = null;

  function preloadInterstitialAd() {
    // isSupported()는 Toss WebView 환경에서만 동작 - try-catch 필수
    try {
      if (typeof loadFullScreenAd.isSupported === 'function' && !loadFullScreenAd.isSupported()) {
        console.warn('[Interstitial] loadFullScreenAd not supported');
        return;
      }
    } catch (e) {
      // WebView 외부(예: 일반 브라우저) 환경 - 지원 안 함
      console.warn('[Interstitial] isSupported check failed:', e.message);
      return;
    }

    // 이전 콜백 등록 해제 (메모리 누수 방지)
    if (interstitialUnregister) {
      interstitialUnregister();
      interstitialUnregister = null;
    }
    interstitialAdLoaded = false;

    console.log('[Interstitial] loading ad...');
    interstitialUnregister = loadFullScreenAd({
      options: { adGroupId: INTERSTITIAL_AD_ID },
      onEvent: (event) => {
        console.log('[Interstitial] load event:', event.type);
        if (event.type === 'loaded') {
          interstitialAdLoaded = true;
        }
      },
      onError: (err) => {
        console.error('[Interstitial] load error:', err);
        interstitialAdLoaded = false;
      },
    });
  }

  // 앱 시작 시 미리 광고를 로드 (버튼 누를 때 바로 보이도록)
  preloadInterstitialAd();

  /**
   * 전면 광고를 보여준 뒤 callback을 실행한다.
   * 광고 미지원이거나 아직 로드가 안 됐으면 callback을 바로 실행한다.
   */
  function showInterstitialThenDo(callback) {
    // isSupported()는 Toss WebView 환경에서만 동작 - try-catch 필수
    let isSupported = false;
    try {
      isSupported = typeof showFullScreenAd.isSupported === 'function'
        ? showFullScreenAd.isSupported()
        : true;
    } catch (e) {
      console.warn('[Interstitial] showFullScreenAd.isSupported check failed:', e.message);
      callback();
      return;
    }

    console.log('[Interstitial] show isSupported:', isSupported, 'adLoaded:', interstitialAdLoaded);

    if (!isSupported || !interstitialAdLoaded) {
      callback();
      return;
    }

    interstitialAdLoaded = false; // 중복 호출 방지
    const unregisterShow = showFullScreenAd({
      options: { adGroupId: INTERSTITIAL_AD_ID },
      onEvent: (event) => {
        console.log('[Interstitial] show event:', event.type);
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

  function revealCards() {
    const cards = document.querySelectorAll('.tab-content.active .fade-in, #chemistry-result-section.fade-in');
    cards.forEach(c => c.classList.remove('reveal'));

    cards.forEach((card, index) => {
      setTimeout(() => {
        card.classList.add('reveal');
      }, index * 150);
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


  btnSubmit.addEventListener('click', (e) => {
    e.preventDefault();
    if (!dogNameInput.value || !dogDateInput.value) {
      alert("강아지 이름과 생년월일을 정확히 입력해주세요!");
      return;
    }

    const userKey = requireUserKey();
    if (!userKey) {
      return;
    }

    const dogName = dogNameInput.value.trim();
    document.querySelectorAll('.dog-name-display').forEach(el => el.textContent = dogName);

    if (testType === 'chemistry') {
      const ownerDate = document.getElementById('owner-date').value;
      if (!ownerDate) {
        alert('보호자 생년월일을 입력해주세요!');
        return;
      }
      chemistryResultSection.style.display = 'block';
    } else {
      chemistryResultSection.style.display = 'none';
    }

    // 1단계: 로딩 화면 먼저 표시
    navigateTo(loadingScreen, false);

    // 2단계: API 호출을 백그라운드에서 즉시 시작 (광고와 병렬 실행)
    const dogGender = document.querySelector('input[name="dog-gender"]:checked').value;
    const postData = {
      social_id: userKey,
      nickname: "Toss 사용자",
      dog: {
        name: dogName,
        birth_date: dogDateInput.value,
        birth_time: dogTimeInput.value || null,
        is_lunar: dogLunarCheck.checked,
        gender: dogGender === 'M' ? 'MALE' : 'FEMALE',
        is_estimated_birth: false
      }
    };

    const apiPromise = (async () => {
      const regRes = await fetch(`${BASE_URL}/api/saju/dogs/`, {
        method: 'POST',
        headers: buildHeaders(true),
        body: JSON.stringify(postData)
      });
      const regData = await regRes.json();
      if (!regRes.ok) throw new Error("등록 실패: " + JSON.stringify(regData));
      const dogId = regData.dog_id;

      // /basics/ 먼저 호출 (백엔드 사주 계산 트리거)
      const basicRes = await fetch(`${BASE_URL}/api/saju/dogs/${dogId}/basics/`, {
        headers: buildHeaders()
      });
      const basicData = await basicRes.json();

      // 결과 화면 진입 전 이미지 프리로딩을 통해 렌더링 렉 최소화
      try {
        const elementMap = { '목': 'wood', '화': 'fire', '토': 'earth', '금': 'metal', '수': 'water' };
        const preloadImgName = elementMap[basicData.main_element] || 'fire';
        const preloadImg = new Image();
        preloadImg.src = `./assets/${preloadImgName}_dog.png`;
      } catch (e) {
        console.warn('Image preload failed', e);
      }

      // basics 완료 후 나머지 병렬 호출
      const [perRes, luckRes] = await Promise.all([
        fetch(`${BASE_URL}/api/saju/dogs/${dogId}/personality/`, {
          headers: buildHeaders()
        }),
        fetch(`${BASE_URL}/api/saju/dogs/${dogId}/daily-luck/`, {
          headers: buildHeaders()
        }),
      ]);
      const perData = await perRes.json();
      const luckData = await luckRes.json();

      let chemData = null;
      if (testType === 'chemistry') {
        const ownerDate = document.getElementById('owner-date').value;
        const ownerTime = document.getElementById('owner-time').value;
        try {
          const chemRes = await fetch(`${BASE_URL}/api/saju/dogs/${dogId}/compatibility/`, {
            method: 'POST',
            headers: buildHeaders(true),
            body: JSON.stringify({ owner_birth_date: ownerDate, owner_birth_time: ownerTime })
          });
          if (chemRes.ok) chemData = await chemRes.json();
        } catch (err) {
          console.error("궁합 조회 실패:", err);
        }
      }
      return { basicData, perData, luckData, chemData };
    })();

    // 3단계: API 완료 후 DOM 업데이트 → 바로 결과 화면으로 이동
    // (전면광고는 이제 리포트 잠금 해제 버튼에서 호출됨)
    apiPromise
      .then(({ basicData, perData, luckData, chemData }) => {
        // ── DOM 업데이트 ──
        const elementMap = { '목': 'wood', '화': 'fire', '토': 'earth', '금': 'metal', '수': 'water' };
        const elementColorMap = { '목': 'text-wood', '화': 'text-fire', '토': 'text-earth', '금': 'text-metal', '수': 'text-water' };
        const elementHanjaMap = { '목': '木', '화': '火', '토': '土', '금': '金', '수': '水' };

        const imgName = elementMap[basicData.main_element] || 'fire';
        const colorClass = elementColorMap[basicData.main_element] || 'text-fire';
        const hanjaEl = elementHanjaMap[basicData.main_element] || '火';

        updateSajuTable(basicData);
        document.querySelector('.result-img').src = `./assets/${imgName}_dog.png`;
        document.getElementById('res-summary').innerHTML = `${formatText(perData.personality_summary)}<br><span class="${colorClass}">${basicData.main_element}(${hanjaEl})</span>의 기운을 타고난 <span class="dog-name-display">${dogName}</span>!`;
        document.getElementById('res-food').innerHTML = formatText(perData.treat_luck);
        document.getElementById('res-energy').innerHTML = formatText(perData.vitality_analysis);
        document.getElementById('res-love').innerHTML = formatText(perData.care_tips);
        document.getElementById('res-social').innerHTML = formatText(perData.social_analysis);
        document.getElementById('res-luck-score').textContent = luckData.luck_score;
        document.getElementById('res-luck-msg').innerHTML = formatText(luckData.message);
        document.getElementById('res-luck-color').textContent = luckData.lucky_color;
        document.getElementById('res-luck-dir').textContent = luckData.lucky_direction;

        if (chemData) {
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
        }

        // ── 결과 화면으로 바로 이동 (광고 없음) ──
        navigateTo(resultScreen, true);
        // 화면 전환 애니메이션 완료 후 Chart.js 렌더링
        requestAnimationFrame(() => setTimeout(() => updateGraphs(basicData.element_distribution), 400));
      })
      .catch(err => {
        console.error(err);
        // 에러 모달 표시
        const errorModal = document.getElementById('error-modal');
        if (errorModal) {
          errorModal.style.display = 'flex';
        } else {
          alert("운세를 분석하는 중 오류가 발생했습니다. 확인 후 다시 시도해주세요.");
        }
        navigateTo(inputScreen, false);
      });
  }); // btnSubmit end

  // ─── Locked Report: 잠금/해제 시스템 ────────────────────────────────────
  function lockReports() {
    const container = document.getElementById('locked-reports-container');
    const overlay = document.getElementById('unlock-overlay');
    if (!container) return;
    container.classList.remove('is-unlocked');
    container.classList.add('is-locked');

    // 이전에 unlock 하면서 부여된 인라인 필터 스타일을 제거하여 CSS의 blur 효과가 다시 먹히도록 함
    const texts = container.querySelectorAll('.lockable-text');
    texts.forEach(t => t.style.filter = '');

    if (overlay) {
      // 인라인 스타일 초기화 (unlockReports에서 설정한 값 제거)
      overlay.style.opacity = '';
      overlay.style.pointerEvents = '';
      overlay.style.display = 'flex';
    }
  }

  function lockChemReport() {
    const container = document.getElementById('locked-chem-container');
    const overlay = document.getElementById('unlock-chem-overlay');
    if (!container) return;
    container.classList.remove('is-unlocked');
    container.classList.add('is-locked');

    // 리셋
    const texts = container.querySelectorAll('.lockable-text');
    texts.forEach(t => t.style.filter = '');

    if (overlay) {
      overlay.style.opacity = '';
      overlay.style.pointerEvents = '';
      overlay.style.display = 'flex';
    }
  }

  function unlockReports() {
    const container = document.getElementById('locked-reports-container');
    const overlay = document.getElementById('unlock-overlay');
    if (!container) return;
    container.classList.remove('is-locked');
    container.classList.add('is-unlocked');
    if (overlay) {
      overlay.style.opacity = '0';
      overlay.style.pointerEvents = 'none';
      setTimeout(() => {
        overlay.style.display = 'none';
        // 500ms 트랜지션 완료 후 인라인 스타일로 필터 완전 제거 (GPU 메모리 절약)
        const texts = container.querySelectorAll('.lockable-text');
        texts.forEach(t => t.style.filter = 'none');
      }, 500);
    }
    // Staggered card reveal after unlock
    const cards = container.querySelectorAll('.detail-card');
    cards.forEach((card, i) => {
      card.style.animation = 'none';
      setTimeout(() => {
        card.style.animation = `unlock-card-reveal 0.5s cubic-bezier(0.22, 1, 0.36, 1) both`;
      }, i * 120);
    });
  }

  function unlockChemReport() {
    const container = document.getElementById('locked-chem-container');
    const overlay = document.getElementById('unlock-chem-overlay');
    if (!container) return;
    container.classList.remove('is-locked');
    container.classList.add('is-unlocked');
    if (overlay) {
      overlay.style.opacity = '0';
      overlay.style.pointerEvents = 'none';
      setTimeout(() => {
        overlay.style.display = 'none';
        // 트랜지션 완료 후 인라인 스타일로 필터 완전 제거 (GPU 메모리 절약)
        const texts = container.querySelectorAll('.lockable-text');
        texts.forEach(t => t.style.filter = 'none');
      }, 500);
    }
  }

  const btnUnlock = document.getElementById('btn-unlock-report');
  if (btnUnlock) {
    btnUnlock.addEventListener('click', () => {
      if (btnUnlock.classList.contains('is-loading')) return;
      btnUnlock.classList.add('is-loading');
      btnUnlock.textContent = '⏳ 광고 준비 중...';

      showInterstitialThenDo(() => {
        btnUnlock.classList.remove('is-loading');
        btnUnlock.innerHTML = '<span class="btn-unlock-icon">🎬</span> 광고 보고 전체 해석 보기';
        unlockReports();
      });
    });
  }

  const btnUnlockChem = document.getElementById('btn-unlock-chem');
  if (btnUnlockChem) {
    btnUnlockChem.addEventListener('click', () => {
      if (btnUnlockChem.classList.contains('is-loading')) return;
      btnUnlockChem.classList.add('is-loading');
      btnUnlockChem.textContent = '⏳ 광고 준비 중...';

      showInterstitialThenDo(() => {
        btnUnlockChem.classList.remove('is-loading');
        btnUnlockChem.innerHTML = '<span class="btn-unlock-icon">🎬</span> 전체 해석 보기';
        unlockChemReport();
      });
    });
  }

  btnShare.addEventListener('click', async () => {
    const originalText = btnShare.textContent;
    btnShare.textContent = "공유 링크 생성 중... 🐾";
    btnShare.disabled = true;

    try {
      const dogName = document.querySelector('.dog-name-display').textContent || '댕댕이';
      const imgSrc = document.querySelector('.result-img').src;
      const imgName = imgSrc.split('/').pop().split('_')[0] || 'fire';

      const elementReverseMap = { 'wood': '목(木)', 'fire': '화(火)', 'earth': '토(土)', 'metal': '금(金)', 'water': '수(水)' };
      const dogElementText = elementReverseMap[imgName] || '화(火)';

      const shareText = `${attachNameJosa(dogName, '는')} ${dogElementText} 기운을 타고 났어요! 보호자님도 우리아이 사주를 한 번 알아보세요🐾`;
      const shareImageUrl = `https://web-production-285b5.up.railway.app/assets/${imgName}_dog.png`;

      const tossLink = await getTossShareLink(
        'intoss://daengsaju',
        shareImageUrl
      );
      await share({ message: `${shareText}\n\n${tossLink}` });
    } catch (e) {
      console.error(e);
      alert('공유 중 오류가 발생했습니다.');
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

  // Draw or Update Radar and set bar variables
  function updateGraphs(dist) {
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

    // Chart.js Radar
    const ctx = document.getElementById('radarChart').getContext('2d');
    const dataValues = [woods, fires, earths, metals, waters];

    if (radarChartInstance) {
      radarChartInstance.destroy(); // Prevent canvas memory leak in WKWebView
    }

    radarChartInstance = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: ['목(木)', '화(火)', '토(土)', '금(金)', '수(水)'],
        datasets: [{
          label: '기질 밸런스',
          data: dataValues,
          backgroundColor: 'rgba(139, 92, 246, 0.15)',
          borderColor: 'rgba(139, 92, 246, 0.8)',
          pointBackgroundColor: '#fff',
          pointBorderColor: 'rgba(139, 92, 246, 1)',
          pointHoverBackgroundColor: 'rgba(139, 92, 246, 1)',
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
            angleLines: { color: 'rgba(148, 163, 184, 0.1)' },
            grid: { color: 'rgba(148, 163, 184, 0.1)' },
            pointLabels: {
              font: { family: 'Pretendard', size: 13, weight: '700' },
              color: '#94A3B8'
            },
            ticks: { display: false, min: 0 }
          }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
  }

  function animateBars() {
    const bars = document.querySelectorAll('.bar-fill');
    bars.forEach(bar => {
      bar.style.transition = 'none';
      bar.style.width = '0%';
    });
    setTimeout(() => {
      bars.forEach(bar => {
        bar.style.transition = 'width 1.2s cubic-bezier(0.25, 1, 0.5, 1)';
        bar.style.width = bar.dataset.targetWidth || '0%';
      });
    }, 50);
  }

  function formatText(text) {
    if (!text) return '';
    return text
      .replace(/\*\*(.*?)\*\*/g, '<span class="highlight-text">$1</span>')
      .replace(/\n/g, '<br>');
  }

  // Korean Josa Helper
  function attachNameJosa(name, type) {
    if (!name) return '';
    const lastChar = name.charCodeAt(name.length - 1);
    if (lastChar < 0xAC00 || lastChar > 0xD7A3) return name + type; // non-korean

    // Check if the name ends with a batchim (consonant)
    const hasJongseong = (lastChar - 0xAC00) % 28 > 0;
    if (type === '는' || type === '은') {
      return name + (hasJongseong ? '이는' : '는');
    }
    return name + type;
  }

  // Error Modal Close Event
  const btnCloseError = document.getElementById('btn-close-error');
  if (btnCloseError) {
    btnCloseError.addEventListener('click', () => {
      document.getElementById('error-modal').style.display = 'none';
    });
  }

  // ─── Attendance & Streak Logic ───────────────────────────────────────────
  const TALISMAN_REWARDS = {
    3: { name: '초심자의 뼈다귀 부적', desc: '3일 연속 출석! 멍멍이의 에너지가 솟아납니다.' },
    7: { name: '행운의 댕댕 부적', desc: '럭키 7일! 이번 주 내내 기분 좋은 일이 가득할 거예요.' },
    10: { name: '재물운 명탐정 부적', desc: '10일 달성! 생각지도 못한 간식이나 행운이 찾아옵니다.' },
    15: { name: '대박 황금 부적', desc: '15일 달성! 주변에서 많은 복이 찾아오는 시기예요.' },
    20: { name: '전설의 댕댕 부적', desc: '당신은 진정한 댕사주 마스터!' },
  };
  const MILESTONES = [3, 7, 10, 15, 20];

  const btnOpenAttendance = document.getElementById('btn-open-attendance');
  const btnAttendanceStamp = document.getElementById('btn-attendance-stamp');
  const attendanceModal = document.getElementById('attendance-modal');
  const btnCloseAttendance = document.getElementById('btn-close-attendance');
  const talismanModal = document.getElementById('talisman-modal');
  const btnCloseTalisman = document.getElementById('btn-close-talisman');
  const btnDownloadTalisman = document.getElementById('btn-download-talisman');
  const btnShareTalisman = document.getElementById('btn-share-talisman');

  let attendanceRecord = [];
  let currentStreak = 0;
  let currentTalismanDay = null;

  const todayDateObj = new Date();
  const currentMonth = todayDateObj.getMonth() + 1;
  const currentDaysInMonth = new Date(todayDateObj.getFullYear(), todayDateObj.getMonth() + 1, 0).getDate();
  const todayDate = todayDateObj.getDate();

  function updateAttendanceStampButton() {
    if (!btnAttendanceStamp) return;

    const alreadyStamped = attendanceRecord.includes(todayDate);
    btnAttendanceStamp.disabled = alreadyStamped;
    btnAttendanceStamp.textContent = alreadyStamped ? '오늘 출석 완료' : '오늘 출석하기';
  }

  // ─── API 기반 출석 로드 ───────────────────────────────────────────
  async function loadAttendance() {
    const userKey = requireUserKey();
    if (!userKey) {
      return null;
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
      console.error('[Attendance] load failed:', e);
      alert('출석 정보를 불러오지 못했어요. 잠시 후 다시 시도해주세요.');
      return null;
    }
  }

  function renderCalendar() {
    const grid = document.getElementById('calendar-grid');
    grid.innerHTML = '';

    // 단순 누적 출석 일수 표시
    const totalAttended = attendanceRecord.length;
    document.getElementById('calendar-streak').textContent = totalAttended + '일';

    const nextRewardDay = MILESTONES.find(m => m > totalAttended) || 30;
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
      // streak-connected 제거 - 누적 방식

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
    const userKey = requireUserKey();
    if (!userKey || attendanceRecord.includes(todayDate)) return;

    try {
      const res = await fetch(`${BASE_URL}/api/saju/attendance/`, {
        method: 'POST',
        headers: buildHeaders(true),
        body: JSON.stringify({ social_id: userKey })
      });
      if (!res.ok) throw new Error('출석 저장 실패');
      const data = await res.json();

      if (!data.stamped) {
        // 이미 출석한 경우 서버 응답으로도 처리
        attendanceRecord = data.attended_days || attendanceRecord;
        currentStreak = data.streak_count || currentStreak;
        renderCalendar();
        return;
      }

      attendanceRecord = data.attended_days || [];
      currentStreak = data.streak_count || 0;

      renderCalendar();

      if (typeof confetti === 'function') {
        confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, colors: ['#FF69B4', '#FFD700', '#ffffff'] });
      }

      // 신규 마일스톤 달성 시 부적 모달 표시
      if (data.new_milestone) {
        setTimeout(() => { showTalisman(data.new_milestone); }, 1000);
      }
    } catch (e) {
      console.error('[Attendance] stamp failed:', e);
      alert('출석 처리에 실패했어요. 잠시 후 다시 시도해주세요.');
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
      const attendanceData = await loadAttendance();
      if (!attendanceData) {
        return;
      }
      renderCalendar();
      attendanceModal.classList.remove('hidden');
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
        const wrapper = document.getElementById('talisman-content-wrapper');
        const canvas = await html2canvas(wrapper, { backgroundColor: '#1E1E2A', useCORS: true });
        const dataUrl = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.href = dataUrl;
        a.download = `daengsaju_talisman_${currentStreak}.png`;
        a.click();
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
            text: `댕사주에서 ${currentStreak}일 연속 출석하고 '${reward.name}'을 획득했어요! 🐾`,
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

document.addEventListener('DOMContentLoaded', () => {
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
  const btnAttendanceReset = document.getElementById('btn-attendance-reset');
  const talismanModal = document.getElementById('talisman-modal');
  const talismanContentWrapper = document.getElementById('talisman-content-wrapper');
  const resultImage = document.getElementById('result-img');

  // Config
  const BASE_URL = ''; // Same origin
  const MIN_LOADING_MS = 250;
  const TOSS_USER_KEY_STORAGE = 'daengsaju_user_key';

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

  // Attendance State
  let attendanceRecord = [];
  let currentStreak = 0;
  let currentTalismanDay = null;
  const ATTENDANCE_TEST_MODE = true;
  const ATTENDANCE_TEST_STORAGE_KEY = 'daengsaju_test_attendance';

  const TALISMAN_REWARDS = {
    1: { name: '시작의 코기 부적', desc: '첫 출석 완료! 오늘의 시작마다 산뜻한 행운이 따라붙을 거예요.' },
    3: { name: '초심자의 뼈다귀 부적', desc: '3일 연속 출석! 멍멍이의 에너지가 솟아납니다.' },
    5: { name: '복슬복슬 말티즈 부적', desc: '5일 연속 출석! 포근한 기운이 차곡차곡 쌓이며 기분 좋은 순간들이 더 자주 찾아올 거예요.' },
    7: { name: '행운의 댕댕 부적', desc: '럭키 7일! 이번 주 내내 기분 좋은 일이 가득할 거예요.' },
    10: { name: '재물운 명탐정 부적', desc: '10일 달성! 생각지도 못한 간식이나 행운이 찾아옵니다.' },
    15: { name: '대박 황금 부적', desc: '15일 달성! 주변에서 많은 복이 찾아오는 시기예요.' },
    20: { name: '전설의 댕댕 부적', desc: '당신은 진정한 댕사주 마스터!' },
  };
  const MILESTONES = [1, 3, 5, 7, 10, 15, 20];

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
      script.onload = resolve;
      script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
      document.head.appendChild(script);
    });

    externalScriptPromises.set(src, promise);
    return promise;
  }

  async function ensureChartJs() {
    if (window.Chart) return;
    await loadExternalScript('https://cdn.jsdelivr.net/npm/chart.js');
  }

  async function ensureHtml2Canvas() {
    if (window.html2canvas) return;
    await loadExternalScript('https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js');
  }

  async function ensureConfetti() {
    if (typeof window.confetti === 'function') return;
    await loadExternalScript('https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js');
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

  function updateAttendanceStampButton() {
    if (!btnAttendanceStamp) return;
    if (btnAttendanceReset) {
      btnAttendanceReset.style.display = ATTENDANCE_TEST_MODE ? 'block' : 'none';
    }
    if (ATTENDANCE_TEST_MODE) {
      btnAttendanceStamp.disabled = false;
      btnAttendanceStamp.textContent = '테스트 도장 찍기';
      btnAttendanceStamp.style.opacity = '1';
      return;
    }
    const stampedToday = attendanceRecord.includes(todayDate);
    btnAttendanceStamp.disabled = stampedToday;
    btnAttendanceStamp.textContent = stampedToday ? '오늘 출석 완료' : '오늘 출석하기';
    btnAttendanceStamp.style.opacity = stampedToday ? '0.6' : '1';
  }

  // Initialize History state
  history.replaceState({ screenId: 'main-screen' }, '', '#main-screen');

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
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    screenElement.classList.add('active');

    if (pushHistory) {
      history.pushState({ screenId: screenElement.id }, '', `#${screenElement.id}`);
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
    alert("蹂댄샇???앸뀈?붿씪???낅젰?댁＜?몄슂!");
    return;
  }

  const dogName = dogNameInput.value.trim();
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

    const regRes = await fetch('/api/saju/dogs/', {
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

    // 2. 사주 기본정보 (GET /basics/)
    const basicRes = await fetch(`/api/saju/dogs/${dogId}/basics/`, { headers: buildHeaders() });
    if (!basicRes.ok) throw new Error("기본정보 로드 실패");
    const basicData = await basicRes.json();
    updateSajuTable(basicData);

    // 3. AI 성격 분석 (GET /personality/)
    const perRes = await fetch(`/api/saju/dogs/${dogId}/personality/`, { headers: buildHeaders() });
    const perData = await perRes.json();

    const elementMap = { '목': 'wood', '화': 'fire', '토': 'earth', '금': 'metal', '수': 'water' };
    const elementColorMap = { '목': 'text-wood', '화': 'text-fire', '토': 'text-earth', '금': 'text-metal', '수': 'text-water' };
    const elementHanjaMap = { '목': '木', '화': '火', '토': '土', '금': '金', '수': '水' };

    const imgName = elementMap[basicData.main_element] || 'fire';
    const colorClass = elementColorMap[basicData.main_element] || 'text-fire';
    const hanjaEl = elementHanjaMap[basicData.main_element] || '火';

    if (resultImage) {
      resultImage.src = `/static/assets/${imgName}_dog.png`;
    } else {
      document.querySelector('.result-img').src = `/static/assets/${imgName}_dog.png`;
    }
    document.getElementById('res-summary').innerHTML = `${formatText(perData.personality_summary)}<br><span class="${colorClass}">${basicData.main_element}(${hanjaEl})</span>의 기운을 타고난 <span class="dog-name-display">${dogName}</span>!`;
    document.getElementById('res-food').innerHTML = formatText(perData.treat_luck);
    document.getElementById('res-energy').innerHTML = formatText(perData.vitality_analysis);
    document.getElementById('res-love').innerHTML = formatText(perData.care_tips);
    document.getElementById('res-social').innerHTML = formatText(perData.social_analysis);

    // 4. 오늘의 산책운 (GET /daily-luck/)
    const luckRes = await fetch(`/api/saju/dogs/${dogId}/daily-luck/`, { headers: buildHeaders() });
    const luckData = await luckRes.json();

    document.getElementById('res-luck-score').textContent = luckData.luck_score;
    document.getElementById('res-luck-msg').innerHTML = formatText(luckData.message);
    document.getElementById('res-luck-color').textContent = luckData.lucky_color;
    document.getElementById('res-luck-dir').textContent = luckData.lucky_direction;

    // 5. 댕궁합 분석 (testType이 chemistry일 때만 호출)
    if (testType === 'chemistry') {
      const ownerDate = document.getElementById('owner-date').value;
      const ownerTime = document.getElementById('owner-time').value;

      try {
        const chemRes = await fetch(`/api/saju/dogs/${dogId}/compatibility/`, {
          method: 'POST',
          headers: buildHeaders(true),
          body: JSON.stringify({
            owner_birth_date: ownerDate,
            owner_birth_time: ownerTime
          })
        });
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
  const originalText = btnShare.textContent;
  btnShare.textContent = "이미지 굽는 중... 🐾";
  btnShare.disabled = true;

  try {
    // 캡쳐할 영역 지정 (결과 컨텐츠 전체 영역)
    await ensureHtml2Canvas();
    const captureArea = document.querySelector('.result-scroll');
    const canvas = await html2canvas(captureArea, {
      scale: 2,
      backgroundColor: '#F9FAFB',
      useCORS: true,
      windowWidth: captureArea.scrollWidth,
      windowHeight: captureArea.scrollHeight
    });

    const imgData = canvas.toDataURL('image/png');

    const modal = document.getElementById('image-modal');
    const genImage = document.getElementById('generated-image');
    const closeBtn = document.getElementById('close-modal');

    if (modal && genImage) {
      genImage.src = imgData;
      modal.style.display = 'flex';

      closeBtn.onclick = () => {
        modal.style.display = 'none';
      };
    } else {
      const link = document.createElement('a');
      link.download = `댕사주_운세결과_${Date.now()}.png`;
      link.href = imgData;
      link.click();
    }
  } catch (e) {
    console.error(e);
    alert('이미지 저장 중 오류가 발생했습니다.');
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
  await ensureChartJs();
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
    .replace(/보호자님님/g, '보호자님')
    .replace(/보호자님이의/g, '보호자님의')
    .replace(/보호자님이께/g, '보호자님께')
    .replace(/\*\*(.*?)\*\*/g, '<span class="highlight-text">$1</span>') // **강조** 처리
    .replace(/\n/g, '<br>'); // 개행 처리
}

// ─── Attendance Logic ───────────────────────────────────────────
async function loadAttendance() {
  if (ATTENDANCE_TEST_MODE) {
    try {
      const saved = localStorage.getItem(ATTENDANCE_TEST_STORAGE_KEY);
      attendanceRecord = saved ? JSON.parse(saved) : [];
      currentStreak = attendanceRecord.length;
      updateAttendanceStampButton();
      return {
        attended_days: attendanceRecord,
        streak_count: currentStreak,
      };
    } catch (e) {
      console.warn('[Attendance] 테스트 데이터 로드 실패:', e);
      attendanceRecord = [];
      currentStreak = 0;
      updateAttendanceStampButton();
      return {
        attended_days: [],
        streak_count: 0,
      };
    }
  }
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
  if (ATTENDANCE_TEST_MODE) {
    const nextDay = Array.from({ length: currentDaysInMonth }, (_, index) => index + 1)
      .find(day => !attendanceRecord.includes(day));
    if (!nextDay) {
      alert('이번 달 테스트 도장을 모두 찍었어요.');
      return;
    }

    attendanceRecord = [...attendanceRecord, nextDay];
    currentStreak = attendanceRecord.length;
    localStorage.setItem(ATTENDANCE_TEST_STORAGE_KEY, JSON.stringify(attendanceRecord));
    renderCalendar();

    await ensureConfetti();
    if (typeof confetti === 'function') {
      confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, colors: ['#FF69B4', '#FFD700', '#ffffff'] });
    }

    if (MILESTONES.includes(currentStreak)) {
      setTimeout(() => { showTalisman(currentStreak); }, 300);
    }
    return;
  }
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

    await ensureConfetti();
    if (typeof confetti === 'function') {
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
  imgEl.src = `/static/assets/talisman_${streak}.png`;
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
if (btnAttendanceReset) {
  btnAttendanceReset.addEventListener('click', () => {
    if (!ATTENDANCE_TEST_MODE) return;
    localStorage.removeItem(ATTENDANCE_TEST_STORAGE_KEY);
    attendanceRecord = [];
    currentStreak = 0;
    currentTalismanDay = null;
    renderCalendar();
  });
}
if (btnCloseAttendance) {
  btnCloseAttendance.addEventListener('click', () => {
    attendanceModal.classList.add('hidden');
  });
}
if (talismanModal) {
  talismanModal.addEventListener('click', () => {
    talismanModal.classList.add('hidden');
  });
}
if (talismanContentWrapper) {
  talismanContentWrapper.addEventListener('click', (event) => {
    event.stopPropagation();
  });
}
});

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
  const backFromInput = document.getElementById('back-from-input');
  const backFromResult = document.getElementById('back-from-result');

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

      // Re-trigger reveal for the new tab
      revealCards();

      // Update Chart visually if changed to lifetime tab
      if(btn.dataset.tab === 'tab-lifetime') {
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

  // Navigation logic
  function navigateTo(screenElement) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    screenElement.classList.add('active');
    
    // reset scroll to top
    if(screenElement === resultScreen) {
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

  backFromInput.addEventListener('click', () => {
    navigateTo(mainScreen);
  });

  backFromResult.addEventListener('click', () => {
    document.getElementById('saju-form').reset();
    navigateTo(mainScreen);
  });

  btnSubmit.addEventListener('click', async (e) => {
    e.preventDefault();
    if(!dogNameInput.value || !dogDateInput.value) {
      alert("강아지 이름과 생년월일을 정확히 입력해주세요!");
      return;
    }

    const dogName = dogNameInput.value.trim();
    document.querySelectorAll('.dog-name-display').forEach(el => el.textContent = dogName);

    if(testType === 'chemistry') {
      chemistryResultSection.style.display = 'block';
    } else {
      chemistryResultSection.style.display = 'none';
    }

    navigateTo(loadingScreen);

    // UX: Labor Illusion (신뢰감을 주기 위한 페이크 로딩 2초)
    await new Promise(resolve => setTimeout(resolve, 2000));

    try {
      // 1. 등록 (POST /api/saju/dogs/)
      const dogGender = document.querySelector('input[name="dog-gender"]:checked').value;
      const postData = {
        social_id: "demo_toss_user_" + Date.now(), 
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(postData)
      });
      const regData = await regRes.json();
      if(!regRes.ok) throw new Error("등록 실패: " + JSON.stringify(regData));
      
      const dogId = regData.dog_id;

      // 2. 사주 기본정보 (GET /basics/)
      const basicRes = await fetch(`/api/saju/dogs/${dogId}/basics/`);
      const basicData = await basicRes.json();
      updateSajuTable(basicData);
      
      // 3. AI 성격 분석 (GET /personality/)
      const perRes = await fetch(`/api/saju/dogs/${dogId}/personality/`);
      const perData = await perRes.json();
      
      const elementMap = { '목': 'wood', '화': 'fire', '토': 'earth', '금': 'metal', '수': 'water' };
      const elementColorMap = { '목': 'text-wood', '화': 'text-fire', '토': 'text-earth', '금': 'text-metal', '수': 'text-water' };
      const elementHanjaMap = { '목': '木', '화': '火', '토': '土', '금': '金', '수': '水' };
      
      const imgName = elementMap[basicData.main_element] || 'fire';
      const colorClass = elementColorMap[basicData.main_element] || 'text-fire';
      const hanjaEl = elementHanjaMap[basicData.main_element] || '火';
      
      document.querySelector('.result-img').src = `./assets/${imgName}_dog.png`;
      document.getElementById('res-summary').innerHTML = `${formatText(perData.personality_summary)}<br><span class="${colorClass}">${basicData.main_element}(${hanjaEl})</span>의 기운을 타고난 <span class="dog-name-display">${dogName}</span>!`;
      document.getElementById('res-food').innerHTML = formatText(perData.treat_luck);
      document.getElementById('res-energy').innerHTML = formatText(perData.vitality_analysis);
      document.getElementById('res-love').innerHTML = formatText(perData.care_tips);
      document.getElementById('res-social').innerHTML = formatText(perData.social_analysis);

      // 4. 오늘의 산책운 (GET /daily-luck/)
      const luckRes = await fetch(`/api/saju/dogs/${dogId}/daily-luck/`);
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
            headers: { 'Content-Type': 'application/json' },
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

      navigateTo(resultScreen);
      // 오행 바 그래프 업데이트 및 애니메이션
      updateGraphs(basicData.element_distribution);
      
      // Tab 1 is default, animation happens on tab click, but we can call it once just in case
      // animateBars();

    } catch (error) {
      console.error(error);
      alert("운세를 분석하는 중 오류가 발생했습니다. 확인 후 다시 시도해주세요.");
      navigateTo(inputScreen);
    }
  });

  btnShare.addEventListener('click', async () => {
    const originalText = btnShare.textContent;
    btnShare.textContent = "이미지 굽는 중... 🐾";
    btnShare.disabled = true;

    try {
      // 캡쳐할 영역 지정 (결과 컨텐츠 전체 영역)
      const captureArea = document.querySelector('.result-scroll');
      const canvas = await html2canvas(captureArea, {
        scale: 2, 
        backgroundColor: '#F9FAFB',
        useCORS: true,
        windowWidth: captureArea.scrollWidth,
        windowHeight: captureArea.scrollHeight
      });

      const imgData = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.download = `댕사주_운세결과_${Date.now()}.png`;
      link.href = imgData;
      link.click();
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
      if(!str || str === '알수없음') return ['-', '-'];
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
              angleLines: { color: 'rgba(139, 149, 161, 0.2)' },
              grid: { color: 'rgba(139, 149, 161, 0.1)' },
              pointLabels: {
                font: { family: 'Pretendard', size: 13, weight: '700' },
                color: '#4E5968'
              },
              ticks: { display: false, min: 0 }
            }
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function(context) {
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
});

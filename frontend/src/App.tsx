import "./App.css";

const smokeChecks = [
  {
    title: "초기 진입",
    detail: "메인 화면 진입, 사용자 키 인식, 첫 화면 렌더가 자연스러운지 확인",
  },
  {
    title: "평생 사주",
    detail: "강아지 등록 후 기본 정보, 성격 분석, 오행 그래프까지 정상 노출되는지 확인",
  },
  {
    title: "댕궁합",
    detail: "보호자 생년월일 입력 후 궁합 점수와 설명 문구가 자연스럽게 보이는지 확인",
  },
  {
    title: "오늘 운세",
    detail: "행운 컬러, 방향, 산책운 메시지가 정상적으로 내려오는지 확인",
  },
  {
    title: "공유와 저장",
    detail: "운세 이미지 저장과 부적 저장 시 오류 없이 동작하는지 확인",
  },
];

const releaseNotes = [
  "초기 분석 API를 통합하고 폴백 경로를 추가해 첫 진입 체감을 줄였습니다.",
  "외부 CDN 로드 실패 시에도 핵심 운세 조회 흐름이 멈추지 않도록 보완했습니다.",
  "템플릿 문구와 플레이스홀더 후처리를 정리해 배포용 문맥 안정성을 높였습니다.",
];

function App() {
  const serviceUrl = "/";

  return (
    <main className="ait-shell">
      <section className="hero-card">
        <div className="hero-badge">Toss AIT Test App</div>
        <h1 className="hero-title">댕사주 배포 점검용 AIT</h1>
        <p className="hero-copy">
          토스 인앱 배포 전, 핵심 흐름을 빠르게 점검할 수 있도록 만든 테스트용
          프론트엔드입니다. 아래 버튼으로 실제 서비스와 점검 포인트를 바로 확인할 수
          있습니다.
        </p>

        <div className="hero-actions">
          <a className="primary-link" href={serviceUrl}>
            실제 서비스 열기
          </a>
          <a className="secondary-link" href={`${serviceUrl}static/assets/logo.png`}>
            정적 자산 확인
          </a>
        </div>
      </section>

      <section className="panel-card">
        <div className="section-heading">
          <span className="section-kicker">Smoke Checklist</span>
          <h2>우선 확인할 흐름</h2>
        </div>

        <div className="check-grid">
          {smokeChecks.map((item) => (
            <article className="check-card" key={item.title}>
              <div className="check-icon">•</div>
              <div>
                <h3>{item.title}</h3>
                <p>{item.detail}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel-card">
        <div className="section-heading">
          <span className="section-kicker">Current Scope</span>
          <h2>이번 배포 반영 사항</h2>
        </div>

        <ul className="note-list">
          {releaseNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>

      <section className="panel-card compact-card">
        <div className="section-heading">
          <span className="section-kicker">Review Tip</span>
          <h2>권장 테스트 순서</h2>
        </div>
        <ol className="flow-list">
          <li>실제 서비스 열기 버튼으로 메인 화면 진입</li>
          <li>평생 사주 1회, 댕궁합 1회, 오늘 운세 1회 확인</li>
          <li>이미지 저장과 출석/부적 흐름까지 마지막으로 점검</li>
        </ol>
      </section>
    </main>
  );
}

export default App;

import React from 'react';

export default function Header({ apiStatus, onRefresh, isRefreshing, onBackToDashboard, onOpenIntro }) {
  const isConnected = apiStatus.summary && apiStatus.grid && apiStatus.hotspots;
  const isPartial = (apiStatus.summary || apiStatus.grid || apiStatus.hotspots) && !isConnected;

  let statusBadgeClass = 'badge-success';
  let statusText = '실시간 연동';

  if (!apiStatus.summary && !apiStatus.grid && !apiStatus.hotspots) {
    statusBadgeClass = 'badge-error';
    statusText = '오프라인';
  } else if (isPartial) {
    statusBadgeClass = 'badge-warning';
    statusText = '일부 지연';
  }

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="brand-logo-container">
          <svg className="brand-logo-svg" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="9" fill="url(#brandGrad)" />
            <path d="M16 6L24 11V21L16 26L8 21V11L16 6Z" stroke="#ffffff" strokeWidth="1.8" strokeLinejoin="round"/>
            <path d="M16 6V26M8 11L24 21M24 11L8 21" stroke="#ffffff" strokeWidth="1.2" strokeOpacity="0.75" strokeLinejoin="round"/>
            <circle cx="16" cy="16" r="3" fill="#ffffff" />
            <defs>
              <linearGradient id="brandGrad" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
                <stop stopColor="#0071e3"/>
                <stop offset="1" stopColor="#42a5f5"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div className="header-copy">
          <div className="header-meta-row">
            <span className="header-eyebrow">FOOD MARKET MAP</span>
            <span className="header-ver-badge">3D GIS</span>
          </div>
          <h1 className="header-title">외식업 B2B 식자재 유통 3D 공간 분석</h1>
        </div>
      </div>

      <div className="header-actions">
        {onBackToDashboard && (
          <button 
            type="button"
            className="back-to-dashboard-btn"
            onClick={onBackToDashboard}
            title="메인 대시보드 홈으로 돌아가기"
            aria-label="메인 대시보드 홈으로 이동"
          >
            <span className="back-btn-icon" aria-hidden="true">🏠</span>
            <span>대시보드 홈</span>
          </button>
        )}

        {onOpenIntro && (
          <button 
            type="button"
            className="intro-video-trigger-btn"
            onClick={onOpenIntro}
            title="3D 공간 인텔리전스 시네마틱 인트로 다시보기"
            aria-label="시네마틱 인트로 열기"
          >
            <span className="intro-btn-icon" aria-hidden="true">🎬</span>
            <span>시네마틱 인트로</span>
          </button>
        )}

        <div className={`status-pill ${statusBadgeClass}`}>
          <span className="status-dot"></span>
          <span>{statusText}</span>
        </div>

        <button 
          className="refresh-btn" 
          onClick={onRefresh} 
          disabled={isRefreshing}
          aria-label="데이터 새로고침"
          title="데이터 새로고침"
        >
          <svg className={`refresh-icon ${isRefreshing ? 'spinning' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
          <span>{isRefreshing ? '동기화 중...' : '데이터 동기화'}</span>
        </button>
      </div>
    </header>
  );
}

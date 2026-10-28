import React, { useState, useEffect } from 'react';
import { fetchDataStatus } from '../services/api';

export default function Header({ apiStatus, onRefresh, isRefreshing, onBackToDashboard, onOpenIntro, onOpenGuideModal }) {
  const [dataStatus, setDataStatus] = useState(null);

  useEffect(() => {
    let ignore = false;
    fetchDataStatus().then(status => {
      if (!ignore && status) {
        setDataStatus(status);
      }
    });
    return () => { ignore = true; };
  }, [isRefreshing]);

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
          <svg className="brand-logo-svg" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <rect width="32" height="32" rx="9" fill="url(#brandGrad)" />
            <path d="M16 6L24 11V21L16 26L8 21V11L16 6Z" stroke="#ffffff" strokeWidth="1.8" strokeLinejoin="round"/>
            <path d="M16 6V26M8 11L24 21M24 11L8 21" stroke="#ffffff" strokeWidth="1.2" strokeOpacity="0.75" strokeLinejoin="round"/>
            <circle cx="16" cy="16" r="3" fill="#ffffff" />
            <defs>
              <linearGradient id="brandGrad" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
                <stop stopColor="var(--color-cool)"/>
                <stop offset="1" stopColor="var(--color-accent)"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div className="header-copy">
          <h1 className="header-title">
            외식업 B2B 식자재 유통 3D 공간 분석
            <span className="header-ver-badge">3D GIS</span>
          </h1>
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
            <span className="back-btn-icon" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            </span>
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
            <span className="intro-btn-icon" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            </span>
            <span>시네마틱 인트로</span>
          </button>
        )}

        {onOpenGuideModal && (
          <button 
            type="button"
            className="intro-video-trigger-btn user-guide-modal-btn"
            onClick={onOpenGuideModal}
            title="3D 대시보드 사용자 가이드 및 용어 사전 열기"
            aria-label="사용자 가이드 모달 열기"
            style={{ 
              borderColor: 'var(--color-rule-2)', 
              color: 'var(--color-cool)', 
              background: 'var(--color-cool-soft)' 
            }}
          >
            <span className="intro-btn-icon" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
            </span>
            <span>사용자 가이드</span>
          </button>
        )}

        {dataStatus && (
          <div 
            className={`status-pill ${dataStatus.has_update ? 'badge-warning update-alert-pill' : 'badge-neutral'}`}
            title={dataStatus.has_update 
              ? `신규 공공데이터(${dataStatus.latest_available_version})가 감지되었습니다. 클릭 시 업데이트 명령어가 복사됩니다.` 
              : `데이터 기준: ${dataStatus.active_version}`}
            style={dataStatus.has_update ? { cursor: 'pointer', background: 'var(--color-accent-soft)', borderColor: 'var(--color-accent)', color: 'var(--color-accent)', fontWeight: 600 } : {}}
            onClick={() => {
              if (dataStatus.has_update) {
                const cmd = `python scripts/run_monthly_update.py --yearmonth ${dataStatus.latest_available_version}`;
                navigator.clipboard?.writeText(cmd);
                alert(`신규 공공데이터(${dataStatus.latest_available_version})가 출시되었습니다!\n\n업데이트 명령어가 복사되었습니다:\n${cmd}`);
              }
            }}
          >
            <span>{dataStatus.has_update ? `새 데이터 (${dataStatus.latest_available_version})` : `${dataStatus.active_version} 기준`}</span>
          </div>
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

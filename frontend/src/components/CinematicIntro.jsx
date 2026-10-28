import React, { useState, useEffect, useRef, useCallback } from 'react';
import './CinematicIntro.css';

/**
 * CinematicIntro
 * 차세대 3D GIS 외식 프랜차이즈 상권 인텔리전스 대문 시네마틱 오버레이
 * 
 * [3대 핵심 사용자 요구사항 반영]
 * 1. 대시보드 홈이 가장 전면에 크게 강조 (Primary Golden Focus)
 * 2. 영상이 끝난 후 약 1.5초간 시네마틱 여운을 둔 뒤 글자가 부드럽게 시작
 * 3. 단락별 순차 리빌 모드 (Staggered Paragraph Reveal):
 *    - 1단락: 메인 슬로건 "Beyond Sight, Into Space"
 *    - 2단락: 서브 슬로건 & 한글 설명 & 3D 스펙 칩
 *    - 3단락: 대시보드 중심 액션 CTA 버튼
 */
export default function CinematicIntro({
  isOpen,
  onClose,
  onExploreDashboard,
  onExplore3DMap
}) {
  const videoRef = useRef(null);
  /**
   * stage: 단락별 리빌 단계
   * 0: 영상 재생 중 (글자 없음, 100% 풀스크린 감상)
   * 1: 영상 종료 직후 시네마틱 여운 (약 1.5초간 마지막 3D 도시 프레임 감상, 배경 딤 활성화)
   * 2: [제1단락] 메인 슬로건 "Beyond Sight, Into Space" 등장
   * 3: [제2단락] 서브 슬로건 & 한글 설명문 & 피처 칩 확장
   * 4: [제3단락] 강조된 "종합 대시보드 홈" 메인 버튼 & 3D 지도 버튼 최종 리빌
   */
  const [stage, setStage] = useState(0);
  const [hasStartedVideo, setHasStartedVideo] = useState(false);
  const [videoProgress, setVideoProgress] = useState(0);
  const [dontShowToday, setDontShowToday] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  // 단계별 전환 타이머 참조 저장
  const timersRef = useRef([]);

  const clearAllTimers = useCallback(() => {
    timersRef.current.forEach((t) => clearTimeout(t));
    timersRef.current = [];
  }, []);

  // 단락별 순차 리빌 시퀀스 가동
  const startParagraphSequence = useCallback(() => {
    clearAllTimers();
    // 1단계: 영상 종료 후 1.5초간 여운 (마지막 장면 조용히 감상)
    setStage(1);

    // 1.5초 후 -> 2단계: 제1단락(메인 슬로건) 등장
    const t1 = setTimeout(() => {
      setStage(2);
    }, 1500);

    // 다시 1.6초 후 (총 3.1초) -> 3단계: 제2단락(상세 설명문) 등장
    const t2 = setTimeout(() => {
      setStage(3);
    }, 3100);

    // 다시 1.4초 후 (총 4.5초) -> 4단계: 제3단락(대시보드 강조 액션 버튼) 등장
    const t3 = setTimeout(() => {
      setStage(4);
    }, 4500);

    timersRef.current = [t1, t2, t3];
  }, [clearAllTimers]);

  // 사용자가 클릭 배너를 누르면 영상 재생 시작
  const handleStartVideo = useCallback((e) => {
    if (e) e.stopPropagation();
    clearAllTimers();
    setHasStartedVideo(true);
    setStage(0);

    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.play().catch((err) => {
        console.warn('Cinematic video play hindered:', err);
      });
    }

    // 브라우저 정책(헤드리스 등) 대비 안전 폴백: 8.2초 후 영상 종료 시퀀스 가동
    const fallbackTimer = setTimeout(() => {
      setStage((prev) => {
        if (prev === 0) {
          startParagraphSequence();
          return 1;
        }
        return prev;
      });
    }, 8200);

    timersRef.current.push(fallbackTimer);
  }, [clearAllTimers, startParagraphSequence]);

  // 인트로가 열릴 때 초기화 (자동재생하지 않고 클릭 배너 대기)
  useEffect(() => {
    if (isOpen) {
      setHasStartedVideo(false);
      setStage(0);
      setVideoProgress(0);
      setIsClosing(false);
      clearAllTimers();

      if (videoRef.current) {
        videoRef.current.currentTime = 0;
        videoRef.current.pause();
      }

      return () => {
        clearAllTimers();
      };
    }
  }, [isOpen, clearAllTimers]);

  // 비디오 재생 시간 및 진행률 추적
  const handleTimeUpdate = useCallback(() => {
    if (!videoRef.current) return;
    const current = videoRef.current.currentTime;
    const duration = videoRef.current.duration || 8.0;

    if (duration > 0) {
      const pct = Math.min(100, Math.round((current / duration) * 100));
      setVideoProgress(pct);
    }

    // 영상 끝나기 직전(7.7초 이상)에 마지막 장면 정지 & 단락 시퀀스 시작
    if (current >= duration - 0.25 && stage === 0) {
      videoRef.current.pause();
      startParagraphSequence();
    }
  }, [stage, startParagraphSequence]);

  // 영상 종료 이벤트
  const handleVideoEnded = useCallback(() => {
    if (stage === 0) {
      startParagraphSequence();
    }
  }, [stage, startParagraphSequence]);

  // 화면 클릭 시: 대기 상태면 재생 시작, 재생 중이면 즉시 최종 단계(Stage 4)로 쾌속 전환
  const handleFastForward = useCallback(() => {
    if (!hasStartedVideo) {
      handleStartVideo();
      return;
    }
    if (stage === 0 && videoRef.current) {
      videoRef.current.currentTime = Math.max(0, (videoRef.current.duration || 8.0) - 0.1);
      videoRef.current.pause();
      clearAllTimers();
      setStage(4); // 즉시 모든 단락 활성화
    } else if (stage > 0 && stage < 4) {
      // 이미 단락 진행 중일 때 클릭하면 곧바로 최종 버튼까지 공개
      clearAllTimers();
      setStage(4);
    }
  }, [hasStartedVideo, handleStartVideo, stage, clearAllTimers]);

  // 영상 다시 재생하기
  const handleReplayVideo = useCallback((e) => {
    e.stopPropagation();
    clearAllTimers();
    setHasStartedVideo(true);
    setStage(0);
    setVideoProgress(0);
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.play().catch((err) => console.warn('Replay failed', err));
    }
    const fallbackTimer = setTimeout(() => {
      setStage((prev) => {
        if (prev === 0) {
          startParagraphSequence();
          return 1;
        }
        return prev;
      });
    }, 8200);
    timersRef.current.push(fallbackTimer);
  }, [clearAllTimers, startParagraphSequence]);

  // 닫기 트리거
  const triggerClose = useCallback((actionCallback) => {
    if (dontShowToday) {
      const todayStr = new Date().toISOString().slice(0, 10);
      try {
        localStorage.setItem('hide_cinematic_intro_date', todayStr);
      } catch (e) {
        console.warn('localStorage access failed', e);
      }
    }

    setIsClosing(true);
    setTimeout(() => {
      onClose();
      if (typeof actionCallback === 'function') {
        actionCallback();
      }
    }, 450);
  }, [dontShowToday, onClose]);

  // ESC 키로 닫기
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        triggerClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, triggerClose]);

  if (!isOpen) return null;

  return (
    <aside 
      className={`cinematic-intro-root ${isClosing ? 'is-closing' : 'is-entering'} stage-${stage} ${!hasStartedVideo ? 'waiting-start' : 'video-started'}`}
      role="dialog"
      aria-modal="true"
      aria-label="서비스 소개 인트로 영상"
      onClick={handleFastForward}
      title={!hasStartedVideo ? "클릭하면 영상이 시작됩니다" : stage < 4 ? "클릭하면 다음 단계로 즉시 이동합니다" : undefined}
    >
      {/* 1. 배경 비디오 레이어 (1080p FHD H.264) */}
      <div className={`cinematic-video-canvas ${!hasStartedVideo ? 'is-waiting-start' : ''}`}>
        <video
          ref={videoRef}
          src="/assets/intro_hero.mp4"
          className="cinematic-video-element"
          preload="auto"
          muted
          playsInline
          onTimeUpdate={handleTimeUpdate}
          onEnded={handleVideoEnded}
        />
        {/* 영상 종료 후(stage >= 1) 또는 재생 전 대기 시 은은하게 스며드는 다크 앰비언트 글래스 딤 */}
        <div className={`cinematic-backdrop-dim ${stage >= 1 ? 'active' : ''}`} />
        <div className="cinematic-grid-scanline" />
      </div>

      {/* 2. 상단 유틸리티 바 */}
      <header className="cinematic-top-bar" onClick={(e) => e.stopPropagation()}>
        <div className="cinematic-brand-chip">
          <span className="brand-dot-pulse" />
          <span className="brand-code">
            {!hasStartedVideo
              ? '3D SPATIAL INTELLIGENCE · READY'
              : stage >= 4 
                ? '3D SPATIAL INTELLIGENCE · READY' 
                : stage >= 1 
                  ? 'CINEMATIC SYNOPSIS' 
                  : 'CINEMATIC PREVIEW · PLAYING'}
          </span>
        </div>

        <div className="cinematic-top-actions">
          {/* 영상이 끝난 후(stage >= 1) 언제든 다시 볼 수 있는 리플레이 버튼 */}
          {stage >= 1 && (
            <button
              type="button"
              className="cinematic-replay-button"
              onClick={handleReplayVideo}
              title="영상 처음부터 다시 재생"
              aria-label="영상 다시 재생"
            >
              <span className="replay-icon">↺</span>
              <span>영상 다시보기</span>
            </button>
          )}

          <button
            type="button"
            className="cinematic-skip-button"
            onClick={() => triggerClose()}
            title="대시보드로 건너뛰기 (ESC)"
            aria-label="대시보드로 건너뛰기"
          >
            <span>건너뛰기 SKIP</span>
            <span className="skip-key-badge">ESC</span>
          </button>
        </div>
      </header>

      {/* 2-1. 대문 진입 시 영상 재생 대기 미니멀 'CLICK' 캡슐 배너 */}
      {!hasStartedVideo && stage === 0 && (
        <div 
          className="cinematic-start-overlay" 
          onClick={handleStartVideo}
          role="region"
          aria-label="시네마틱 영상 재생 대기"
        >
          <button 
            type="button"
            className="cinematic-click-pill apple-style-cta"
            onClick={handleStartVideo}
            aria-label="Click to play"
          >
            <svg 
              className="cinematic-click-icon" 
              viewBox="0 0 16 16" 
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M4.5 2.8v10.4c0 .6.7 1 1.2.7l8.2-5.2c.5-.3.5-1.1 0-1.4L5.7 2.1c-.5-.3-1.2.1-1.2.7z"/>
            </svg>
            <span className="cinematic-click-text">CLICK</span>
          </button>
        </div>
      )}

      {/* 3. 재생 중 초박형 진행 바 */}
      {hasStartedVideo && stage === 0 && (
        <div className="cinematic-progress-wrap" aria-hidden="true">
          <div className="cinematic-progress-bar" style={{ width: `${videoProgress}%` }} />
        </div>
      )}

      {/* 4. 중앙 콘텐츠: 단락별 순차 리빌 구조 (Staggered Paragraphs) */}
      {stage >= 2 && (
        <main className="cinematic-hero-content" onClick={(e) => e.stopPropagation()}>
          {/* 볼류메트릭 골드 방사형 광원 */}
          <div className="cinematic-volumetric-glow" aria-hidden="true" />

          {/* =========================================================
              [제1단락] ✦ 슬로건 각인: 아이브로우 캡슐 + 메인 타이틀
              ========================================================= */}
          <section className="paragraph-block paragraph-1 animate-p1">
            <div className="cinematic-eyebrow-wrapper">
              <div className="cinematic-eyebrow-pill">
                <span className="eyebrow-spark">✦</span>
                <span className="eyebrow-text">소진공 전수 실측 빅데이터</span>
                <span className="eyebrow-divider" />
                <span className="eyebrow-metric">735,185 STORES</span>
              </div>
            </div>

            <h1 className="cinematic-main-title">
              <span className="title-word title-beyond">Beyond</span>{' '}
              <span className="title-word title-sight">Sight,</span>
              <br className="mobile-break" />
              <span className="title-word title-into">Into</span>{' '}
              <span className="title-word title-space">Space</span>
            </h1>
          </section>

          {/* =========================================================
              [제2단락] 📜 공간 인텔리전스 해설 & 3대 핵심 피처 칩
              ========================================================= */}
          {stage >= 3 && (
            <section className="paragraph-block paragraph-2 animate-p2">
              <div className="cinematic-subtitle-block">
                <p className="cinematic-tagline-en">
                  3D Spatial Intelligence for Korea’s Food & Franchise Market
                </p>
                <p className="cinematic-desc-ko">
                  엑셀 수작업 없는 3D 공간 데이터와 공정위 4개년 재무 벤치마크로<br className="desc-break" />
                  대한민국 73.5만 외식 점포와 B2B 식자재 유통 상권을 입체 증명합니다.
                </p>

                {/* 3D 스펙 지표 피처 칩 */}
                <div className="cinematic-feature-chips">
                  <div className="feature-chip">
                    <span className="chip-icon" aria-hidden="true">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="9" y1="22" x2="9" y2="2"/><line x1="15" y1="22" x2="15" y2="2"/><line x1="4" y1="12" x2="20" y2="12"/></svg>
                    </span>
                    <span className="chip-label">100m 입체 건물 격자</span>
                  </div>
                  <div className="feature-chip">
                    <span className="chip-icon" aria-hidden="true">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5M12 12h.01"/><path d="M19.1 4.9c3.9 3.9 3.9 10.3 0 14.2M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/></svg>
                    </span>
                    <span className="chip-label">소진공 73.5만 전수 실측</span>
                  </div>
                  <div className="feature-chip">
                    <span className="chip-icon" aria-hidden="true">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                    </span>
                    <span className="chip-label">공정위 4개년 재무 벤치마크</span>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* =========================================================
              [제3단락] 🚀 행동 유도 (CTA): ★종합 대시보드 홈 메인 강조★
              ========================================================= */}
          {stage >= 4 && (
            <section className="paragraph-block paragraph-3 animate-p3">
              <nav className="cinematic-actions-group" aria-label="서비스 진입 메뉴">
                {/* ★ 1순위 메인 강조: 종합 대시보드 홈 (Primary Gold Focus) ★ */}
                <button
                  type="button"
                  className="cinematic-cta-primary double-bezel-btn dashboard-hero-btn"
                  onClick={() => triggerClose(onExploreDashboard)}
                  title="외식업 종합 통계 대시보드로 이동"
                >
                  <span className="btn-inner-glow" />
                  <span className="btn-beacon-pulse" aria-hidden="true" />
                  <span className="btn-label-wrap">
                    <span className="btn-main-label">종합 대시보드 무료 체험</span>
                    <span className="btn-sub-label">73.5만 점포 분석 및 B2B 잠재 고객 탐색</span>
                  </span>
                  <span className="btn-circle-arrow" aria-hidden="true">
                    <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
                      <path d="M3.33334 8H12.6667M12.6667 8L8.00001 3.33334M12.6667 8L8.00001 12.6667" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </span>
                </button>

                {/* 2순위 보조 버튼: 3D 상권 공간 지도 (Secondary Glass Style) */}
                <button
                  type="button"
                  className="cinematic-cta-secondary double-bezel-btn map-sub-btn"
                  onClick={() => triggerClose(onExplore3DMap)}
                  title="3D GIS 상권 지도로 바로 이동"
                >
                  <span className="btn-inner-glow" />
                  <span className="btn-label-wrap">
                    <span className="btn-main-label">3D 상권 지도 둘러보기</span>
                    <span className="btn-sub-label">100m 입체 격자 및 핫스팟 탐색</span>
                  </span>
                  <span className="btn-circle-arrow" aria-hidden="true">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                      <path d="M3.33334 8H12.6667M12.6667 8L8.00001 3.33334M12.6667 8L8.00001 12.6667" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </span>
                </button>
              </nav>
            </section>
          )}
        </main>
      )}

      {/* 5. 하단 상태 바 */}
      <footer className="cinematic-bottom-bar" onClick={(e) => e.stopPropagation()}>
        {stage >= 4 ? (
          <label className="cinematic-dont-show-label">
            <input
              type="checkbox"
              className="cinematic-checkbox"
              checked={dontShowToday}
              onChange={(e) => setDontShowToday(e.target.checked)}
            />
            <span className="checkbox-custom-box" aria-hidden="true" />
            <span className="checkbox-text">오늘 하루 이 화면 다시 보지 않기</span>
          </label>
        ) : hasStartedVideo ? (
          <div className="cinematic-play-hint">
            <span className="hint-icon" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
            </span>
            <span>
              {stage === 0 
                ? '화면을 클릭하면 즉시 소개 내용으로 이동합니다' 
                : '화면을 클릭하면 대시보드 바로가기 버튼이 즉시 열립니다'}
            </span>
          </div>
        ) : null}

        <div className="cinematic-meta-right">
          <span className="meta-coords">37°30'45"N 127°02'28"E</span>
          <span className="meta-divider">|</span>
          <span className="meta-system">KOREA FOOD MARKET INTEL v2.5</span>
        </div>
      </footer>
    </aside>
  );
}

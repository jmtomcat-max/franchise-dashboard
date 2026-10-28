import React, { useState, useEffect } from 'react';
import './UserGuideModal.css';

export default function UserGuideModal({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('glossary'); // 'glossary' | 'controls' | 'ftc' | 'cases'

  // ESC 키 누르면 닫기
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div 
      className="user-guide-backdrop" 
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="guide-modal-title"
    >
      <div className="user-guide-modal" onClick={(e) => e.stopPropagation()}>
        
        {/* 1. Modal Header Bar */}
        <div className="guide-modal-header">
          <div className="guide-modal-brand">
            <div className="guide-brand-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div className="guide-brand-info">
              <h2 id="guide-modal-title">공식 사용자 가이드</h2>
              <span>대한민국 73.5만 개 외식업 3D 상권 인텔리전스</span>
            </div>
          </div>
          <button 
            type="button" 
            className="guide-close-btn" 
            onClick={onClose}
            aria-label="가이드 닫기"
            title="닫기 (ESC)"
          >
            ✕
          </button>
        </div>

        {/* 2. Modal Tab Navigation */}
        <div className="guide-modal-tabs">
          <button 
            type="button" 
            className={`guide-tab-btn ${activeTab === 'glossary' ? 'active' : ''}`}
            onClick={() => setActiveTab('glossary')}
          >
            <span>핵심 용어 사전</span>
          </button>
          <button 
            type="button" 
            className={`guide-tab-btn ${activeTab === 'controls' ? 'active' : ''}`}
            onClick={() => setActiveTab('controls')}
          >
            <span>3D 지도 조작법</span>
          </button>
          <button 
            type="button" 
            className={`guide-tab-btn ${activeTab === 'ftc' ? 'active' : ''}`}
            onClick={() => setActiveTab('ftc')}
          >
            <span>공정위 창업비용</span>
          </button>
          <button 
            type="button" 
            className={`guide-tab-btn ${activeTab === 'cases' ? 'active' : ''}`}
            onClick={() => setActiveTab('cases')}
          >
            <span>3대 실전 시나리오</span>
          </button>
        </div>

        {/* 3. Modal Scrollable Body */}
        <div className="guide-modal-body">
          
          {/* TAB 1: GLOSSARY */}
          {activeTab === 'glossary' && (
            <div>
              <div className="modal-callout-note">
                <span className="callout-icon" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                  </svg>
                </span>
                <span>외식 상권 분석에 필요한 주요 공공 통계 용어와 3D GIS 기술 개념을 정리했습니다.</span>
              </div>

              <div className="modal-glossary-grid">
                <div className="modal-glossary-card">
                  <h4 className="modal-term-title">
                    FTC (공정거래위원회)
                    <span className="modal-term-badge">약어 · 공공기관</span>
                  </h4>
                  <p className="modal-term-desc">
                    프랜차이즈 가맹본부가 의무 제출하는 정보공개서(실제 창업비용, 평균 매출액)의 공식 출처입니다.
                  </p>
                </div>

                <div className="modal-glossary-card">
                  <h4 className="modal-term-title">
                    BBOX (Bounding Box)
                    <span className="modal-term-badge">공간 기술 · 지도</span>
                  </h4>
                  <p className="modal-term-desc">
                    모니터 화면에 보이는 지도의 사각형 영역을 뜻합니다. 73.5만 개 데이터를 다 받지 않고 내가 보고 있는 영역의 점포만 실시간 스트리밍합니다.
                  </p>
                </div>

                <div className="modal-glossary-card">
                  <h4 className="modal-term-title">
                    fill-extrusion (3D 기둥 돌출)
                    <span className="modal-term-badge">3D 시각화 기술</span>
                  </h4>
                  <p className="modal-term-desc">
                    100m 격자 안의 외식 점포 밀집도를 3차원 기둥 높이로 표현하는 기술입니다. 기둥이 높을수록 경쟁이 치열한 과밀 상권입니다.
                  </p>
                </div>

                <div className="modal-glossary-card">
                  <h4 className="modal-term-title">
                    YoY (전년 대비 증감률)
                    <span className="modal-term-badge">통계 지표</span>
                  </h4>
                  <p className="modal-term-desc">
                    작년 대비 올해 가맹점 매출액이나 점포수가 몇 % 늘었거나 줄었는지를 나타내는 시계열 성장 지표입니다.
                  </p>
                </div>

                <div className="modal-glossary-card">
                  <h4 className="modal-term-title">
                    Decoupled Model (분리 대사 모델)
                    <span className="modal-term-badge">데이터 아키텍처</span>
                  </h4>
                  <p className="modal-term-desc">
                    일반 개인 식당과 10개 이상 점포를 가진 공인 프랜차이즈(5,063개)를 100% 분리하여 통계 왜곡을 차단합니다.
                  </p>
                </div>

                <div className="modal-glossary-card">
                  <h4 className="modal-term-title">
                    프랜차이즈 침투율 (%)
                    <span className="modal-term-badge">시장 분석 지표</span>
                  </h4>
                  <p className="modal-term-desc">
                    해당 상권의 전체 음식점 중 공인 가맹 프랜차이즈가 차지하는 비율입니다. 높을수록 대기업 브랜드 위주의 상권입니다.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: CONTROLS */}
          {activeTab === 'controls' && (
            <div>
              <div className="modal-callout-note">
                <span className="callout-icon" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                  </svg>
                </span>
                <span>지도 우측 슬림 플로팅 레일(SlimMapRail)을 통해 시점과 렌더링 모드를 제어할 수 있습니다.</span>
              </div>

              <div className="modal-steps-list">
                <div className="modal-step-item">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num">01</span>
                    [3D / 2D] 시점 전환
                  </h4>
                  <p>지도를 52도로 기울여 3D 기둥의 높낮이를 입체 비교하거나, 위에서 직하강으로 내려다보는 2D 평면 탑뷰로 전환합니다.</p>
                </div>

                <div className="modal-step-item">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num">02</span>
                    [3D 렌즈] 기둥 높이 제어
                  </h4>
                  <p>기둥 높이를 바닥으로 내려앉혀 기둥 뒤에 가려진 골목의 개별 매장 마커들을 선명하게 확인할 수 있습니다.</p>
                </div>

                <div className="modal-step-item">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num">03</span>
                    [색상] 밀집도 vs 8대 업종별 테마
                  </h4>
                  <p>기둥 색상을 과밀도 히트맵에서 8대 업종별 고유 테마 컬러로 즉시 전환합니다.</p>
                </div>

                <div className="modal-step-item">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num">04</span>
                    [드론] 상권 핫스팟 비행 투어
                  </h4>
                  <p>강남역, 홍대입구, 명동 등 선택된 지역의 최고 핫스팟 상권으로 카메라가 하강 비행하는 시네마틱 관찰 모드입니다.</p>
                </div>

                <div className="modal-step-item">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num">05</span>
                    [줌 14+] 개별 점포 스트리밍
                  </h4>
                  <p>지도를 확대하여 줌레벨 14에 도달하면 실제 매장 마커가 나타나며, 마커를 클릭하면 상호명과 가맹 여부 팝업이 뜹니다.</p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: FTC BENCHMARK */}
          {activeTab === 'ftc' && (
            <div>
              <div className="modal-callout-note">
                <span className="callout-icon" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                  </svg>
                </span>
                <span>공정거래위원회 4개년(2023~2026) 실측 창업비용 구성과 해석 원칙입니다.</span>
              </div>

              <div className="modal-steps-list">
                <div className="modal-step-item">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num">01</span>
                    가맹비 (가입비)
                  </h4>
                  <p>브랜드 상표권 사용 및 초기 조리/영업 노하우 전수 비용입니다.</p>
                </div>

                <div className="modal-step-item">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num">02</span>
                    계약이행보증금
                  </h4>
                  <p>식자재 물품대금 채권 확보를 위한 예치금이며, 계약 종료 시 100% 반환받습니다.</p>
                </div>

                <div className="modal-step-item">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num">03</span>
                    인테리어 비용 (평당 단가)
                  </h4>
                  <p>매장 면적(평당)에 비례하는 바닥, 벽면, 조명, 냉난방 필수 시공비용입니다.</p>
                </div>

                <div className="modal-step-item">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num">04</span>
                    가맹점 연간 평균 매출액
                  </h4>
                  <p>실제 운영 중인 전국 가맹점들의 연간 실측 매출액과 면적당(평당) 연매출 지표입니다.</p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: CASES */}
          {activeTab === 'cases' && (
            <div>
              <div className="modal-callout-note">
                <span className="callout-icon" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                  </svg>
                </span>
                <span>분석 목적에 따라 3대 실전 시나리오를 적용하여 리스크를 최소화하세요.</span>
              </div>

              <div className="modal-steps-list">
                <div className="modal-step-item case-card-amber">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num case-tag-amber">CASE 1</span>
                    예비 창업자: 과밀 레드오션 회피
                  </h4>
                  <p>100m 3D 기둥이 붉게 솟아있는 곳을 피하고, 배후 수요 대비 경쟁 기둥이 낮은 블루오션 골목을 탐색합니다.</p>
                </div>

                <div className="modal-step-item case-card-ok">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num case-tag-ok">CASE 2</span>
                    가맹본부(HQ): 전국 256개 시군구 출점 공백지 선점
                  </h4>
                  <p>전국 시군구 침투율을 비교하여 자사 브랜드 점포가 비어있는 핵심 상권을 우선 선점합니다.</p>
                </div>

                <div className="modal-step-item case-card-cool">
                  <h4 className="modal-step-title">
                    <span className="modal-step-num case-tag-cool">CASE 3</span>
                    상권 분석가 & 투자자: VIP 고객 브리핑
                  </h4>
                  <p>3D 드론 뷰와 4개년 공정위 시계열 통계를 결합하여 객관적이고 과학적인 상권 평가서를 도출합니다.</p>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* 4. Modal Footer Bar */}
        <div className="guide-modal-footer">
          <a 
            href="/USER_GUIDE.html" 
            target="_blank" 
            rel="noopener noreferrer" 
            className="guide-full-doc-link"
          >
            <span>전체 설명서 전문 새 창으로 보기</span>
          </a>
          <button 
            type="button" 
            className="guide-modal-close-btn" 
            onClick={onClose}
          >
            확인 및 닫기
          </button>
        </div>

      </div>
    </div>
  );
}

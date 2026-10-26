import React from 'react';

/**
 * SlimMapRail 컴포넌트
 * 레퍼런스 영상(얼마나좋아할지감도안옴_map.mp4 00:10~00:16) 44px 슬림 플로팅 레일 차용
 * 지도를 침범하지 않는 우측 슬림 수직 바에서 3D/2D, 기둥높이, 색상모드, 핫스팟, 시점 리셋 원클릭 제어
 */
export default function SlimMapRail({
  is3DMode = true,
  onToggle3D,
  isExtrusionEnabled = true,
  onToggleExtrusion,
  colorMode = 'density', // 'density' | 'category'
  onToggleColorMode,
  isGridVisible = true,
  onToggleGrid,
  isStoreLayerVisible = true,
  onToggleStores,
  isHotspotsVisible = false,
  onToggleHotspots,
  isFtcDrawerOpen = false,
  onToggleFtcDrawer,
  onResetView,
  hasGridData = false
}) {
  return (
    <aside className="slim-map-rail" aria-label="3D 지도 시각화 제어 레일">
      {/* 1. 3D 경사각 / 2D 정사영 시점 토글 */}
      <button
        type="button"
        className={`rail-btn ${is3DMode ? 'active' : ''}`}
        onClick={onToggle3D}
        aria-label={is3DMode ? '2D 평면 탑뷰로 전환' : '3D 경사각 시점으로 전환'}
        aria-pressed={is3DMode}
        title={is3DMode ? '3D 경사각 시점 (52°) 활성 (클릭 시 2D 탑뷰)' : '2D 평면 탑뷰 활성 (클릭 시 3D 경사각)'}
      >
        <span className="rail-icon">
          {is3DMode ? (
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
              <line x1="8" y1="2" x2="8" y2="18"/>
              <line x1="16" y1="6" x2="16" y2="22"/>
            </svg>
          )}
        </span>
        <span className="rail-label">{is3DMode ? '3D' : '2D'}</span>
      </button>

      {/* 2. 3D 기둥 렌즈 (기본 꺼짐: 점포 시야 확보용 2D 탑뷰) */}
      <button
        type="button"
        className={`rail-btn ${isExtrusionEnabled ? 'active' : ''}`}
        onClick={onToggleExtrusion}
        disabled={!hasGridData}
        aria-label={isExtrusionEnabled ? '3D 기둥 렌즈 끄기 (2D 탑뷰로 복귀)' : '3D 기둥 렌즈 켜기'}
        aria-pressed={isExtrusionEnabled}
        title={isExtrusionEnabled ? '3D 기둥 렌즈 켜짐 (클릭 시 2D 탑뷰로 복귀)' : '3D 기둥 렌즈 (점포수를 높이로 비교, 점포가 가려질 수 있음)'}
      >
        <span className="rail-icon">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {isExtrusionEnabled ? (
              <>
                <line x1="18" y1="20" x2="18" y2="10"/>
                <line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
              </>
            ) : (
              <>
                <line x1="4" y1="18" x2="20" y2="18"/>
                <rect x="6" y="14" width="4" height="4"/>
                <rect x="14" y="14" width="4" height="4"/>
              </>
            )}
          </svg>
        </span>
        <span className="rail-label">3D렌즈</span>
      </button>

      {/* 3. 색상 테마 토글 (밀집도 ↔ 8대 업종별 테마) */}
      <button
        type="button"
        className={`rail-btn ${colorMode === 'category' ? 'active-category' : 'active-density'}`}
        onClick={onToggleColorMode}
        disabled={!hasGridData}
        aria-label={colorMode === 'category' ? '밀집도 5단계 색상으로 전환' : '8대 업종별 테마 색상으로 전환'}
        title={colorMode === 'category' ? '8대 업종별 색상 활성 (클릭 시 밀집도 단계)' : '밀집도 단계 색상 활성 (클릭 시 8대 업종별)'}
      >
        <span className="rail-icon">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/>
            <circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/>
            <circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/>
            <circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/>
            <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.563-2.512 5.563-5.563C22 6.5 17.5 2 12 2z"/>
          </svg>
        </span>
        <span className="rail-label">{colorMode === 'category' ? '업종별' : '밀집도'}</span>
      </button>

      <div className="rail-divider" role="separator" />

      {/* 4. 지도 데이터 레이어 표출 토글 */}
      <button
        type="button"
        className={`rail-btn ${isGridVisible ? 'active' : ''}`}
        onClick={onToggleGrid}
        disabled={!hasGridData}
        aria-label={isGridVisible ? '밀집도 격자 숨기기' : '밀집도 격자 표시'}
        aria-pressed={isGridVisible}
        title={isGridVisible ? '밀집도 격자 표시 중' : '밀집도 격자 숨김'}
      >
        <span className="rail-icon">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1.5"/>
            <rect x="14" y="3" width="7" height="7" rx="1.5"/>
            <rect x="14" y="14" width="7" height="7" rx="1.5"/>
            <rect x="3" y="14" width="7" height="7" rx="1.5"/>
          </svg>
        </span>
        <span className="rail-label">밀집</span>
      </button>

      <button
        type="button"
        className={`rail-btn ${isStoreLayerVisible ? 'active' : ''}`}
        onClick={onToggleStores}
        aria-label={isStoreLayerVisible ? '개별 점포 숨기기' : '개별 점포 표시'}
        aria-pressed={isStoreLayerVisible}
        title={isStoreLayerVisible ? '줌 14 이상에서 개별 점포 표시 중' : '개별 점포 숨김'}
      >
        <span className="rail-icon">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" fill="currentColor"/>
            <circle cx="12" cy="12" r="8"/>
          </svg>
        </span>
        <span className="rail-label">점포</span>
      </button>

      {/* 5. 상권 핫스팟 팝오버 토글 */}
      {onToggleHotspots && (
        <button
          type="button"
          className={`rail-btn ${isHotspotsVisible ? 'active' : ''}`}
          onClick={onToggleHotspots}
          aria-label={isHotspotsVisible ? '상권 핫스팟 메뉴 닫기' : '상권 핫스팟 메뉴 열기'}
          aria-pressed={isHotspotsVisible}
          title={isHotspotsVisible ? '상권 핫스팟 팝오버 닫기' : '상권 핫스팟 팝오버 열기'}
        >
          <span className="rail-icon">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>
            </svg>
          </span>
          <span className="rail-label">핫스팟</span>
        </button>
      )}

      {/* 6. 공정위 가맹점 매출·창업비용 분석 패널 토글 */}
      {onToggleFtcDrawer && (
        <button
          type="button"
          className={`rail-btn ${isFtcDrawerOpen ? 'active-sales' : ''}`}
          onClick={onToggleFtcDrawer}
          aria-label={isFtcDrawerOpen ? '매출·창업비용 분석 패널 닫기' : '매출·창업비용 분석 패널 열기'}
          aria-pressed={isFtcDrawerOpen}
          title={isFtcDrawerOpen ? '매출·창업비용 패널 닫기' : '공정위 가맹점 평균 매출·창업비용 분석 보기'}
        >
          <span className="rail-icon">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="1" x2="12" y2="23"/>
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
          </span>
          <span className="rail-label">매출</span>
        </button>
      )}

      {/* 6. 선택 지역 전체 조망 시점 리셋 */}
      {onResetView && (
        <button
          type="button"
          className="rail-btn reset-btn"
          onClick={onResetView}
          aria-label="선택 지역 전체 조망으로 시점 복귀"
          title="선택 지역 전체 조망 복귀 (BBOX Fit)"
        >
          <span className="rail-icon">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="22" y1="12" x2="18" y2="12"/>
              <line x1="6" y1="12" x2="2" y2="12"/>
              <line x1="12" y1="6" x2="12" y2="2"/>
              <line x1="12" y1="22" x2="12" y2="18"/>
            </svg>
          </span>
          <span className="rail-label">리셋</span>
        </button>
      )}
    </aside>
  );
}

import React, { useEffect, useRef } from 'react';

const HOTSPOT_REGION_NAMES = {
  '11215': '서울 광진구',
  '11680': '서울 강남구',
  '11440': '서울 마포구',
  '11140': '서울 중구',
  '41135': '성남 분당구',
  '26230': '부산 부산진구',
  '27110': '대구 중구',
  '30170': '대전 서구',
  '12200': '광주 서구',
  '28185': '인천 연수구'
};

function getHotspotRegionLabel(item) {
  if (item.address) return item.address;
  if (HOTSPOT_REGION_NAMES[item.sigungu_code]) {
    return HOTSPOT_REGION_NAMES[item.sigungu_code];
  }
  return `지역 ${item.sido_code} ${item.sigungu_code}`;
}

/**
 * HotspotsPanel — 우측 컨트롤 독(SlimMapRail)의 '🔥 핫스팟' 버튼을 눌렀을 때
 * 왼쪽 옆으로 톡 튀어나오는 팝오버(Popover / Flyout) 메뉴
 */
export default function HotspotsPanel({
  hotspots,
  activeHotspotId,
  onSelectHotspot,
  onClose,
  loading,
  error,
  onRetry,
  selectedRegionInfo,
  activeRegionCode
}) {
  const popoverRef = useRef(null);
  const isNationwide = !activeRegionCode || activeRegionCode === '00';
  const isSido = activeRegionCode && activeRegionCode.length === 2 && !isNationwide;
  const isSigungu = activeRegionCode && activeRegionCode.length === 5;
  const currentRegionName = selectedRegionInfo?.region_name || '전국';

  // ESC 키로 팝오버 닫기
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && onClose) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // 백엔드가 이미 선택 지역(시도/시군구) 및 업종에 맞춰 동적 핫스팟 Top 5를 반환하므로 그대로 표출
  const filteredHotspots = Array.isArray(hotspots) ? hotspots.slice(0, 6) : [];

  return (
    <aside
      ref={popoverRef}
      className="hotspots-popover"
      aria-label="주요 상권 핫스팟 팝오버 메뉴"
    >
      {/* 우측 독(Dock)의 핫스팟 버튼을 가리키는 말풍선 화살표 */}
      <span className="hotspots-popover-arrow" aria-hidden="true" />

      <div className="hotspots-popover-header">
        <div className="hotspots-popover-title-wrap">
          <span className="hotspots-popover-badge">🔥 HOT</span>
          <div>
            <h2 className="hotspots-popover-title">주요 상권 핫스팟</h2>
            <p className="hotspots-popover-sub">
              {isNationwide
                ? '전국 대표 핵심 상권 Top 5'
                : `${currentRegionName} 핵심 상권 (${filteredHotspots.length}곳)`}
            </p>
          </div>
        </div>
        {onClose && (
          <button
            type="button"
            className="hotspots-popover-close"
            onClick={onClose}
            aria-label="핫스팟 메뉴 닫기"
            title="닫기 (ESC)"
          >
            ✕
          </button>
        )}
      </div>

      {loading ? (
        <div className="hotspots-popover-body">
          <div className="skeleton-loader">
            <div className="skeleton-line" style={{ width: '100%', height: '56px' }} />
            <div className="skeleton-line" style={{ width: '100%', height: '56px' }} />
          </div>
        </div>
      ) : error ? (
        <div className="hotspots-popover-body">
          <div className="panel-error">
            <p className="error-msg">{error}</p>
            <button className="retry-btn" onClick={onRetry}>다시 시도</button>
          </div>
        </div>
      ) : (
        <div className="hotspots-popover-body">
          {filteredHotspots.length === 0 ? (
            <div className="hotspots-popover-empty" role="status">
              <div className="empty-title">등록된 핫스팟이 없습니다</div>
              <div className="empty-desc">
                현재 선택하신 <strong>{currentRegionName}</strong>에는 등록된 대표 상권이 없습니다. (광진·강남·마포·분당 등 또는 전국 모드에서 제공)
              </div>
            </div>
          ) : (
            <ul className="hotspots-popover-list">
              {filteredHotspots.map((item, idx) => {
                const isActive = activeHotspotId === item.hotspot_id;
                const regionLabel = getHotspotRegionLabel(item);
                return (
                  <li key={item.hotspot_id}>
                    <button
                      type="button"
                      className={`hotspot-popover-item ${isActive ? 'active' : ''}`}
                      onClick={() => onSelectHotspot(item)}
                      aria-pressed={isActive}
                    >
                      <span className="hotspot-item-rank">#{idx + 1}</span>
                      <div className="hotspot-item-main">
                        <div className="hotspot-item-top">
                          <span className="hotspot-item-name">{item.hotspot_name}</span>
                          <span className="hotspot-item-region">{regionLabel}</span>
                        </div>
                        <div className="hotspot-item-meta">
                          <span>점포 <strong>{item.store_count ? item.store_count.toLocaleString() : '-'}</strong></span>
                          <span className="meta-dot">·</span>
                          <span>프랜차이즈 <strong className="accent">{item.franchise_ratio || 0}%</strong></span>
                          <span className="meta-dot">·</span>
                          <span>{item.dominant_category_name || '-'}</span>
                        </div>
                      </div>
                      <span className="hotspot-item-go" aria-hidden="true">→</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </aside>
  );
}

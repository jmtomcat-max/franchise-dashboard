# Phase 7 Step 7-3 배포 사양 및 운영 설정 확정 보고서

## 1. 개요 및 확정 결론

Phase 7 Step 7-2에서 승인된 **단일 서버 + Reverse Proxy + 동일 출처 (Same-Origin)** 구성을 바탕으로, 실제 외부 배포나 유료 결제 없이 운영 환경에 즉시 적용 가능한 표준 배포 사양 및 운영 설정을 확정했다.

검토 피드백을 수렴하여 동일 출처 통신 안정성, 웹서버 권한, 서비스 DB 백업 범위, CORS 보안 정책, 배포 템플릿 정합성, 멀티프로세스 로깅 안전성, Nginx 헤더 상속 규칙을 완벽하게 완비했다:

- **신규 서버 초기 TLS 부트스트랩 및 2단계 프로비저닝 순서 확정**: 신규 서버 구축 초기에는 `/etc/letsencrypt/` 인증서가 없으므로 처음부터 HTTPS 설정을 켜면 `nginx -t`가 실패한다. 이에 따라 포트 80 및 ACME 챌린지 전용 초기 부트스트랩 템플릿(`deploy/nginx-bootstrap.conf`)을 제공하고, `setup_server.sh`에 "초기 HTTP 부트스트랩 기동 -> Certbot Webroot 인증서 발급 -> HTTPS 메인 설정 활성화 및 리로드"의 2단계 프로비저닝 가이드를 확립했다. (대안인 Caddy는 내장 ACME로 도메인 지정 즉시 자동 발급 가능).
- **백업 보존 일수 안전성 검증 및 회귀 테스트 통과**: `scripts/backup_production_db.py`에 `--retention-days < 1` 입력 차단 및 `rotate_old_backups` 유효성 검증을 구현하여, 보존 일수가 0이나 음수일 때 방금 생성된 백업 파일이 삭제되는 위험을 원천 차단했다. 또한 `tests/test_phase7_backup_retention.py` 단위 회귀 테스트 3종을 작성하여 100% 통과시켰다.
- **Nginx add_header 상속 결함 수정**: Nginx는 하위 location 블록에 `add_header`가 정의되면 상위 server 블록의 헤더가 상속되지 않는 특성이 있다. 이에 따라 `deploy/nginx.conf`의 `location /assets/` 및 `location /` 블록 내부에 보안 헤더 4종(`X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`)을 명시하여 HTML 및 정적 자산 응답 전체에서 보안 헤더 누락을 원천 차단했다.
- **정밀 AST 토크나이저 파서 기반 템플릿 검증**: `scripts/verify_deployment_templates.py`에 Nginx AST 토크나이저 v2를 구현하여 메인 및 부트스트랩 지시어 전수, 세미콜론(`;`) 종결 강제, 지시어별 최소 인수(argument) 개수 검사(`proxy_pass;` 등 인수 누락 차단), 괄호 중첩 검사를 통과시켰다. Caddyfile 역시 34개 허용 토큰 화이트리스트 검사를 통해 오타/임의 지시어(`typo_nonexistent` 등)를 원천 차단하도록 구현하여 100% PASS 했다.
- **멀티프로세스 로깅 안전성 확보**: `deploy/logging.conf`에서 멀티워커 환경의 파일 잠금 충돌 위험이 있는 `RotatingFileHandler`를 제거하고, 표준 출력/표준 에러(`StreamHandler`)를 통한 systemd `journald` 단일 수집기 아키텍처로 통일했다 (`deploy/franchise-dashboard.service`의 `StandardOutput=journal`과 100% 일치).
- **동일 출처 종단간(End-to-End) 프록시 통합 검증 완료**: `frontend/vite.config.js`에 `preview.proxy`(`/api` -> `http://127.0.0.1:8000`)를 구성하고, `scripts/verify_local_production.py`에서 프론트엔드 출처(`http://127.0.0.1:4173/api/v1/analytics/summary`)를 통한 실제 API 호출이 SPA fallback HTML이 아닌 유효한 JSON 페이로드(`"total_stores": 735185`)로 반환됨을 검증 통과했다.
- **프로덕션 빌드 동일 출처 100% 강제**: `frontend/.env.production`(`VITE_API_URL=`)을 추가하여 `frontend/.env`의 루프백 주소를 오버라이드하고, `frontend/src/services/api.js`에서 프로덕션 모드(`import.meta.env.PROD`) 시 루프백 주소를 자동 무효화하여 동일 출처 상대 경로(`""`)를 강제했다. 일반 `npm run build` 기본 실행 시에도 번들 내 루프백 주소가 0건임을 검증 완료했다.
- **개발 환경 CORS 자동 허용 및 스크립트 정비**: `src/stage4e/api/main.py`에서 `ENVIRONMENT != production` 또는 `ALLOW_DEV_CORS=1`일 때 `http://localhost:5173` 및 `http://127.0.0.1:5173`을 자동 허용하고, `scripts/run_backend.ps1` 및 `scripts/run_backend.bat`에 `ALLOW_DEV_CORS=1`을 명시하여 기존 개발 실행 경로의 호환성을 100% 보장했다. 반면 프로덕션 환경에서는 교차 출처가 전면 차단된다.
- **Nginx/Caddy 정적 자산 접근 권한 확정**: `deploy/setup_server.sh`에서 상위 디렉터리 탐색 권한(755)을 부여하고, `www-data` 및 `caddy` 웹서버 계정을 `franchise` 그룹에 등록하여 `frontend/dist`에 대한 403 Forbidden 위험을 원천 해결했다.
- **실제 서비스 DB 3종 전체 백업 체계**: `scripts/backup_production_db.py`를 확장하여 실제 API가 사용하는 3개 핵심 DB(`franchise_analytics_v1.sqlite3`, `ftc_macro_statistics_v1.sqlite3`, `brand_master_v1.sqlite3`, 총 약 747MB) 전체를 온라인 무락 복제, SHA-256 체크섬, 개별 `PRAGMA integrity_check` 무결성 검증, 7일 보존 주기 회전으로 관리하도록 완비했다.
- **외부 의존성 완전 제거**: `frontend/index.html`의 unpkg CDN MapLibre CSS 링크를 제거하고 `maplibre-gl/dist/maplibre-gl.css`를 Vite 번들로 통합하여 완전한 오프라인/망 분리 복원력을 확보했다.

---

## 2. 서버 표준 사양 (Server Specifications)

| 구분 | 최소 요구 사양 | 권장 사양 | 비고 |
|---|---|---|---|
| **운영체제** | Ubuntu 22.04 LTS (x86_64) | Ubuntu 24.04 LTS (x86_64/arm64) | 표준 Linux 배포판 |
| **CPU (vCPU)** | 2 vCPU | 4 vCPU | 공간 쿼리 및 Uvicorn 2~4 워커 분산 |
| **메모리 (RAM)** | 4 GB | 8 GB | 캐시 및 동시 요청 버퍼 확보 |
| **저장공간 (Disk)** | 30 GB SSD | 50 GB NVMe | 전체 서비스 DB (약 747MB) + 7일 백업 및 로그 |
| **네트워크 포트** | 80(HTTP), 443(HTTPS), 22(SSH) | 80, 443, 22 (SSH 키 인증 필수) | 8000번 포트는 내부 루프백(127.0.0.1) 격리 |

---

## 3. 구성 요소 및 템플릿 명세

### 3.1 프로세스 관리 (`deploy/franchise-dashboard.service`)
- **실행 사용자/그룹**: `franchise:franchise`
- **배포 경로**: `/opt/franchise-dashboard`
- **실행 명령**: `.venv/bin/uvicorn src.stage4e.api.main:app --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips=127.0.0.1 --log-config=/opt/franchise-dashboard/deploy/logging.conf`
- **재시작 정책**: `always` (간격 5초)
- **로깅 정책**: `StandardOutput=journal`, `StandardError=journal` (journald 단일 수집기 통합으로 멀티프로세스 파일 잠금 충돌 방지)
- **보안 격리**: `ProtectSystem=full`, `ReadOnlyPaths=/opt/franchise-dashboard/data`, `PrivateTmp=true`

### 3.2 Reverse Proxy (`deploy/nginx.conf`, `deploy/nginx-bootstrap.conf`, `deploy/Caddyfile`)
- **웹서버 권한**: `setup_server.sh`를 통해 `www-data`/`caddy` 계정 탐색 및 `frontend/dist` 읽기 권한 보장
- **TLS 부트스트랩, 발급 및 자동 갱신 리로드**:
  - Nginx: 초기 `deploy/nginx-bootstrap.conf`로 포트 80/ACME 챌린지 오픈 -> `certbot certonly --webroot`에 `--deploy-hook "systemctl reload nginx"` 옵션을 지정하여 발급 및 자동 갱신 리로드 훅 등록 -> `deploy/nginx.conf` 링크 및 HTTPS 활성화 (`certbot.timer` 주기적 갱신 성공 시 Nginx가 새 인증서를 메모리에 자동 리로드하도록 보장)
  - Caddy: 내장 ACME가 도메인 지정 즉시 Let's Encrypt 인증서를 자동 발급/갱신 (별도 리로드 훅 불필요)
- **보안 헤더 상속 대응**: server 블록 외에 `location /assets/` 및 `location /` 내에도 보안 헤더 4종 직접 명시
- **라우팅 규칙**:
  - `/` -> `/opt/franchise-dashboard/frontend/dist` (SPA 라우팅 `try_files $uri $uri/ /index.html`)
  - `/assets/` -> 정적 자산 캐싱 (`Cache-Control: public, max-age=31536000, immutable`)
  - `/api/` -> `http://127.0.0.1:8000/api/` (Reverse Proxy)
  - `/healthz` -> `http://127.0.0.1:8000/api/health` (헬스체크 매핑)
- **보안 헤더**: `X-Frame-Options SAMEORIGIN`, `X-Content-Type-Options nosniff`, `Referrer-Policy strict-origin-when-cross-origin`
- **압축**: Gzip / Brotli 활성화

### 3.3 프론트엔드 동일 출처 통신 및 정적 번들
- **동일 출처 상대 경로**: `frontend/.env.production` 및 `api.js` 프로덕션 루프백 무효화로 `BASE_URL = ""` 강제
- **MapLibre CSS 번들링**: `frontend/src/main.jsx`에 `import 'maplibre-gl/dist/maplibre-gl.css'` 통합
- **빌드 산출물**:
  - `dist/index.html`: 511 B
  - `dist/assets/index-*.css`: 130.11 KB (MapLibre CSS 포함)
  - `dist/assets/index-*.js`: 1,037.92 KB (절대경로 0건)

### 3.4 서비스 운영 데이터베이스 3종 및 백업 (`scripts/backup_production_db.py`)
운영 서비스에 필수적인 SQLite 데이터베이스 3종 전체를 안전하게 관리한다:
1. `data/franchise_analytics_v1.sqlite3` (514,043,904 bytes, 73.5만 점포 및 공간 통계 DB)
2. `data/ftc_macro_statistics_v1.sqlite3` (32,325,632 bytes, 공정위 4개년 거시통계 DB)
3. `data/brand_master_v1.sqlite3` (200,921,088 bytes, 브랜드 마스터 및 대사 DB)

- **백업 방식**: `source_conn.backup(dest_conn)` (SQLite Online Backup API, 무중단 일관성 복제)
- **무결성 검사**: 복제본 생성 직후 `PRAGMA integrity_check` 수행하여 `ok` 확인 및 샘플 쿼리 대사
- **체크섬 및 메타데이터**: 파일별 SHA-256 해시(`.sha256`) 및 실행 통계(`.meta.json`) 동시 보관
- **보존 주기 및 안전성**: 기본 7일, `--retention-days >= 1` 유효성 사전 검증으로 신규 백업 삭제 방지 (회귀 테스트 통과)

---

## 4. 정량 검증 결과

| 검증 항목 | 기준 | 결과 | 판정 |
|---|---|---|---|
| **Python 환경** | Python 3.12.7 (.venv) | Python 3.12.7 | **PASS** |
| **사전점검** | `scripts/preflight_check.py` | 7개 핵심 항목 정상 | **PASS** |
| **Python 테스트** | `pytest tests -q` | 82/82 통과 (12.59초) | **PASS** |
| **백업 보존 회귀 테스트** | `tests/test_phase7_backup_retention.py` | 3/3 통과 (retention_days >= 1 검증 및 신규 파일 보호) | **PASS** |
| **API 스모크** | `scripts/smoke_test_api.py` | 12/12 통과 (평균 20.3ms) | **PASS** |
| **배포 템플릿 정밀 파서** | `scripts/verify_deployment_templates.py` | Nginx 메인/부트스트랩(83개 지시어 전수·인수 최소수·세미콜론), Caddy v2(34개 토큰 화이트리스트), systemd, logging PASS | **PASS** |
| **CORS 개발 허용** | `Origin: http://localhost:5173` | `access-control-allow-origin` 헤더 정상 반환 | **PASS** |
| **CORS 운영 차단** | `Origin: https://untrusted.example` (Prod) | 헤더 미반환 (전면 차단) | **PASS** |
| **기본 프로덕션 빌드** | `npm run build` (별도 환경변수 미주입) | 번들 내 127.0.0.1:8000 절대경로 0건 | **PASS** |
| **동일 출처 E2E 프록시** | `http://127.0.0.1:4173/api/v1/analytics/summary` | HTTP 200 및 유효 JSON 페이로드 반환 | **PASS** |
| **로컬 프로덕션 모드** | `scripts/verify_local_production.py` | 프론트(4173), API(8000), 프록시 E2E 정상 기동 및 200 확인 | **PASS** |
| **백업 유틸리티** | `scripts/backup_production_db.py` | 서비스 DB 3종 전체 온라인 복제 및 무결성 `ok` | **PASS** |
| **보호 파일 해시** | `collector.py` 외 2종 | 3종 SHA-256 기준값 100% 일치 | **PASS** |

### 미실행 항목 (규정 준수 및 안전 범위 격리)
- **Linux VM 라이브 데몬 구동 및 공식 CLI 검증**: 외부 클라우드 계정 생성, 유료 결제 및 인스턴스 프로비저닝 금지 지침에 따라 실제 Ubuntu Linux VM에서의 라이브 데몬 구동 및 공식 CLI(`nginx -t`, `caddy validate`) 실행은 수행하지 않았으며, 정밀 템플릿 AST 파서 검증 및 로컬 프록시 에뮬레이션 단계까지만 수행함.

### 보호 파일 SHA-256 검증표
| 파일명 | 기준 SHA-256 해시 | 검증 상태 |
|---|---|---|
| `collector.py` | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` | **일치 (PASS)** |
| `gangnam_food_stores.sqlite3` | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` | **일치 (PASS)** |
| `run_gangnam.bat` | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` | **일치 (PASS)** |

---

## 5. 다음 단계 권장 사항

1. **실제 배포 준비 완료**: 모든 구성 템플릿(systemd, Nginx 메인/부트스트랩, Caddy, multi-db backup, env, setup_server)이 확정되었고 정밀 파서 및 종단간 프록시 검증까지 완료되었으므로, 사용자 승인 시 대상 클라우드 VM 프로비저닝 단계로 이행 가능.
2. **도메인 및 TLS 프로비저닝 순서**: Nginx 사용 시 신규 서버에서는 초기 HTTP 부트스트랩(`deploy/nginx-bootstrap.conf`)을 통해 Certbot으로 TLS 인증서를 먼저 발급받은 후, 본 HTTPS 설정(`deploy/nginx.conf`)을 활성화하여 안전하게 전환 가동. (Caddy(`deploy/Caddyfile`) 사용 시에는 내장 ACME가 도메인 지정 즉시 인증서를 자동 발급하므로 별도 사전 부트스트랩 없이 즉시 가동 가능).
3. **백업 보존 안전성**: `scripts/backup_production_db.py`에 `--retention-days >= 1` 유효성 사전 검증 및 회귀 테스트(`tests/test_phase7_backup_retention.py`)가 완비되어, 0이나 음수 값으로 인한 신규 백업 삭제 위험을 원천 차단.

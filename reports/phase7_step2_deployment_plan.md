# Phase 7 Step 7-2 배포 준비 계획

## 결론

로컬 프로덕션 검증은 **PASS**했다. 현 MVP의 최소 권장안은 **단일 서버 + reverse proxy + 동일 출처** 구성이다. 정적 프론트와 FastAPI를 한 호스트에서 제공하고 SQLite 파일은 서버의 영속 디스크에 둔다. 실제 외부 배포, 업로드, 결제, DNS 변경은 수행하지 않았다.

## 배포 선택지

| 구성 | 비용·운영 | 보안·CORS | SQLite 지속성 | 판정 |
|---|---|---|---|---|
| 단일 서버: reverse proxy가 정적 `frontend/dist` 제공 및 `/api`를 FastAPI로 전달 | 서버 1대라 가장 단순하고 저렴함 | 동일 출처로 CORS 의존 최소화, TLS 한 곳에서 종료 | 약 700MB DB를 로컬 영속 디스크에 읽기 전용 배치 가능 | **권장** |
| 정적 프론트 분리 + API 서버 | 정적 호스팅은 단순하지만 두 배포면과 도메인 관리 필요 | 허용 origin을 정확히 설정해야 함 | DB는 여전히 API 서버 영속 디스크와 백업 필요 | 대안 |
| 컨테이너 단일/복수 서비스 | 재현성은 좋지만 이미지·볼륨·로그 운영이 추가됨 | 네트워크와 secret 설정 필요 | DB를 이미지에 넣지 않고 별도 volume에 고정해야 함 | 현재 보류 |

권장안은 API 인스턴스 1개로 시작한다. SQLite 읽기 중심 MVP에는 충분하지만, 다중 서버·쓰기 증가·무중단 DB 교체가 필요해지면 PostgreSQL/PostGIS 전환을 별도 단계로 승인받아야 한다.

## 검증 결과

| 항목 | 결과 |
|---|---:|
| `.venv` Python | 3.12.7 / PASS |
| 사전점검 | PASS |
| Python 테스트 | 82/82 PASS, 20.39초 |
| API 스모크 | 12/12 PASS, 평균 22.9ms |
| Vite 프로덕션 빌드 | PASS |
| 빌드 산출물 | HTML 668B / CSS 130,111B / JS 1,046,827B |
| 프론트 진입점 | HTTP 200 (`127.0.0.1:4173`) |
| API 헬스체크 | HTTP 200 (`127.0.0.1:8000`) |

자동 검증 명령은 다음과 같다.

```powershell
.\.venv\Scripts\python.exe .\scripts\verify_local_production.py
```

이 명령은 빌드, 포트 8000/4173 충돌 검사, 임시 서버 기동, HTTP 확인, 서버 종료, DB·보호 파일 전후 비교를 수행한다. 상세 결과는 `reports/phase7_step2_local_production_validation.json`, 로그는 `reports/phase7_step2_backend.log`와 `reports/phase7_step2_frontend.log`에 남는다.

## 데이터 및 파일 불변성

`data/brand_master_v1.sqlite3`는 검증 전후 모두 200,921,088바이트, 브랜드 5,063개, 링크 735,208개, 리뷰 2개이며 `PRAGMA integrity_check`는 `ok`다. 보호 파일 SHA-256도 기준값과 일치했다.

| 보호 파일 | SHA-256 |
|---|---|
| `collector.py` | `341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C` |
| `gangnam_food_stores.sqlite3` | `FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78` |
| `run_gangnam.bat` | `0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491` |

## 환경변수와 비밀정보

- `VITE_API_URL`: 프론트 빌드 시 공개 API origin. 비밀정보가 아니며 배포 주소로 빌드해야 한다.
- `SERVICE_KEY`: 수집 작업 전용 비밀정보. 저장소·프론트 빌드·로그에 넣지 않고 운영 환경의 secret 저장소 또는 프로세스 환경변수로만 주입한다. 현재 대시보드 조회 서버에는 불필요하다.

`.env` 파일은 배포 산출물에 복사하지 않으며 실제 키 값은 보고서에도 기록하지 않는다.

## 운영 점검과 위험

- 헬스체크: 현재 `GET /`가 HTTP 200과 `status=healthy`를 반환한다. reverse proxy의 외부 경로와 충돌하지 않도록 API health 경로 매핑을 배포 시 확정한다.
- CORS: 현재 백엔드는 `allow_origins=["*"]`와 credentials 허용이다. 외부 공개 전 동일 출처로 운영하거나 명시적인 HTTPS origin 목록으로 제한해야 한다.
- 정적 자산: JS/CSS 번들은 로컬 빌드되지만 `index.html`의 MapLibre CSS는 `unpkg.com`에 의존한다. 망 차단이나 CDN 장애 시 지도 스타일이 깨질 수 있어 공개 전 로컬 번들링 여부를 결정해야 한다.
- SQLite 권한: API 분석 DB 연결은 읽기 전용이다. 운영 계정에는 DB 디렉터리 읽기와 로그 디렉터리 쓰기만 부여하고 DB 파일 교체 권한은 배포 계정으로 분리한다.
- 백업·복구: 서버 중지 또는 SQLite online backup으로 DB와 checksum manifest를 함께 보관한다. 외부 공개 전에 별도 경로 복원 후 `PRAGMA integrity_check`와 82개 테스트를 1회 실행한다.
- 로그: stdout/stderr를 회전 로그로 수집하되 요청 query나 예외에 인증키가 포함되지 않도록 한다. 디스크 사용량 경보가 필요하다.
- 포트: 내부 API 8000, 로컬 preview 4173을 사용한다. 운영에서는 reverse proxy만 80/443을 공개하고 8000은 loopback에 묶는다.

## 사용자 결정 필요

1. 단일 서버 권장안 또는 정적 프론트 분리 대안 선택
2. 운영 도메인과 TLS 인증서 관리 주체
3. 서버 지역·예산·백업 보존 기간 및 복구 목표
4. MapLibre CSS를 외부 CDN에 유지할지 로컬 번들로 전환할지

이 결정과 승인 전에는 실제 배포로 진행하지 않는다.

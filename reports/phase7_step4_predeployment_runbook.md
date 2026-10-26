# Phase 7 Step 7-4 실제 배포 전 최종 실행계획서 (Pre-Deployment Runbook)

## 1. 개요 및 운영 원칙

본 실행계획서(Runbook)는 대한민국 외식 프랜차이즈 시장 분석 3D GIS 대시보드(**Franchise Dashboard**)를 실제 프로덕션 단일 서버 환경에 안전하게 배포하고, 원자적 정적 자산 전환(Atomic dist swap)과 초고속 백엔드 재기동을 통해 서비스 다운타임을 최소화(배포 시간대 DEPLOYMENT_WINDOW 내 실행)하기 위한 **최종 표준 운영 절차서**이다.

### 1.1 핵심 운영 원칙
1. **사전 승인제 엄수**: 본 문서는 배포 "준비 및 확정" 단계의 산출물이며, 사용자가 서버 인스턴스 접속 권한 및 도메인 정보를 제공하고 **명시적으로 실제 배포를 승인하기 전까지는 어떠한 외부 클라우드 결제, VM 생성, 파일 업로드, DNS 변경도 실행하지 않는다.**
2. **보호 자산 불변성**: 기존 데이터 수집 자산 3종(`collector.py`, `gangnam_food_stores.sqlite3`, `run_gangnam.bat`)은 배포 과정에서 절대 수정하거나 삭제하지 않는다.
3. **데이터베이스 무결성 보존**: 운영 DB(`data/brand_master_v1.sqlite3`, `data/franchise_analytics_v1.sqlite3`, `data/ftc_macro_statistics_v1.sqlite3`)의 원본 스키마와 데이터를 보존하며, 프로덕션 서버에는 읽기 전용(`ReadOnlyPaths`, `mode=ro`)으로 영속 배치한다.
4. **동일 출처(Same-Origin) 통신**: 외부 CDN 의존성을 완전히 제거하고, Nginx Reverse Proxy를 통해 정적 SPA 번들과 백엔드 API를 동일 도메인(포트 443)에서 상대 경로로 제공하여 CORS 이슈 및 네트워크 복잡성을 원천 배제한다.

---

## 2. 서버 표준 사양 및 아키텍처

### 2.1 아키텍처 다이어그램
```
[ 인터넷 사용자 / 웹 브라우저 ]
           │ HTTPS (포트 443) / HTTP (포트 80: ACME & 301 Redirect)
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 단일 프로덕션 호스트 (Ubuntu 24.04 LTS)                     │
│                                                             │
│  [ UFW 방화벽 ]: 80(공개), 443(공개), 22(관리자 IP 한정)     │
│                                                             │
│  [ Nginx 1.24+ Reverse Proxy & 정적 웹서버 ]               │
│     │                                                       │
│     ├─ / (root) ──────► /opt/franchise-dashboard/frontend/dist │
│     │                   (SPA index.html / 번들 CSS·JS 캐싱)  │
│     │                                                       │
│     ├─ /healthz ──────► http://127.0.0.1:8000/api/health    │
│     │                                                       │
│     └─ /api/ ─────────► [ systemd 데몬 (Uvicorn 2 Workers) ]│
│                          http://127.0.0.1:8000/api/         │
│                          (FastAPI 백엔드, loopback 격리)     │
│                                   │                         │
│                                   ▼ (SQLite Online Read)    │
│                         ┌───────────────────────┐           │
│                         │ SQLite 3종 서비스 DB   │           │
│                         │  - franchise_analytics│           │
│                         │  - ftc_macro          │           │
│                         │  - brand_master       │           │
│                         │ (ReadOnlyPaths 보호)  │           │
│                         └───────────────────────┘           │
│                                   ▲                         │
│  [ 일일 자동 백업 cron ] ─────────┘ (무중단 온라인 백업 API)│
│   매일 03:00 <BACKUP_DESTINATION>                           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 하드웨어 및 OS 권장 사양
- **기본 운영체제**: **Ubuntu 24.04 LTS (x86_64 또는 arm64)**
  - *선정 사유*: 시스템 기본 Python이 `3.12`로 탑재되어 있어, 별도 외부 PPA(deadsnakes) 추가나 소스 빌드 없이 가상환경(`.venv`)을 완벽한 호환성으로 즉시 구성 가능 (Ubuntu 22.04는 기본 Python 3.10).
- **운영 권장 사양**: **4 vCPU / 8 GB RAM / 50 GB NVMe SSD**
  - 대용량 공간 통계(Grid / H3 / 폴리곤) 쿼리 및 Uvicorn 2~4개 워커의 동시 요청 메모리 버퍼, 7일치 일일 백업(약 5.2GB) 보존 공간 확보.
- **최소 요구 사양**: **2 vCPU / 4 GB RAM / 30 GB SSD**
  - 서비스 DB 3종(약 747MB) 및 Uvicorn 2워커 구동 최소 요건.
- **네트워크 포트 정책**:
  - `80/TCP`: HTTP (Let's Encrypt ACME 챌린지 및 HTTPS 301 영구 리다이렉트)
  - `443/TCP`: HTTPS (TLS 1.2 / 1.3 암호화 웹 서비스)
  - `22/TCP`: SSH (특정 관리자 IP 대역만 접근 허용, Ed25519/RSA 키 인증 전용)
  - `8000/TCP`: 내부 루프백(`127.0.0.1`)에만 바인딩 (외부 직접 노출 차단)

---

## 3. 사용자 필수 입력값 명세 (11종)

실제 배포를 착수하기 위해 사용자가 반드시 제공해야 하는 필수 파라미터 11종의 정의 및 형식:

| 번호 | 파라미터 키 (KEY) | 데이터 형식 | 설명 | 입력 예시 |
|:---:|:---|:---:|:---|:---|
| 1 | `SERVER_PROVIDER` | 문자열 | 클라우드 또는 호스팅 제공사명 | `AWS`, `GCP`, `Ncloud`, `Vultr`, `Hetzner` |
| 2 | `SERVER_PUBLIC_IP` | IPv4 | 배포 대상 서버의 고정 공인 IP 주소 | `203.0.113.10` |
| 3 | `SSH_USER` | 문자열 | 초기 서버 접속용 관리자 사용자 계정 | `ubuntu`, `debian`, `root` |
| 4 | `SSH_PORT` | 정수 | SSH 원격 접속 포트 번호 (기본 22) | `22` (또는 커스텀 포트) |
| 5 | `SSH_PRIVATE_KEY_PATH` | 파일경로 | 배포를 실행할 로컬 PC의 개인키 경로 | `~/.ssh/id_ed25519` 또는 `C:/Users/.../.ssh/id_rsa` |
| 6 | `OPERATING_DOMAIN` | FQDN | 서비스 운영 정식 도메인 (A 레코드 연결 필수) | `dashboard.franchise.kr` |
| 7 | `ADMIN_EMAIL` | 이메일 | Let's Encrypt 인증서 만료 알림 수신 이메일 | `admin@franchise.kr` |
| 8 | `BACKUP_DESTINATION` | 디렉터리 경로 | 서버 로컬 백업 저장소 경로 (권장: `/opt/franchise-dashboard/backups`) | `/opt/franchise-dashboard/backups` |
| 9 | `BACKUP_RETENTION_DAYS` | 정수 (>=1) | 백업 파일 보존 일수 (최소 1 이상, 권장 7) | `7` |
| 10 | `DEPLOYMENT_WINDOW` | 시간 범위 | 무중단 배포 또는 초기 배포 허용 시간대 | `평일 22:00 ~ 24:00 KST` |
| 11 | `ALLOWED_ADMIN_IPS` | IP/CIDR | SSH 접속을 허용할 관리자 공인 IP 대역 (쉼표 구분) | `198.51.100.24/32, 203.0.113.0/24` |

---

## 4. 단계별 상세 배포 절차 (Phase 1 ~ Phase 8)

배포 작업은 아래 8개 단계를 순차적으로 진행하며, 각 단계마다 완료 기준을 검증한다.

### Phase 1: 서버 인스턴스 보안 및 기본 방화벽 설정
1. **관리자 계정 접속 확인**:
   ```bash
   ssh -i <SSH_PRIVATE_KEY_PATH> -p <SSH_PORT> <SSH_USER>@<SERVER_PUBLIC_IP>
   ```
2. **SSH 보안 강화 (비밀번호 로그인 전면 차단 및 키 인증 강제)**:
   - *OpenSSH 설정 우선순위 보장*: OpenSSH는 첫 번째로 일치한 설정을 취하므로(First-match wins), 클라우드 기본 설정(예: `50-cloud-init.conf`)보다 항상 먼저 적용되도록 `00-franchise-security.conf`로 최우선 순위를 부여합니다.
   ```bash
   # 최우선 순위 설정 파일 생성 (비밀번호 로그인 전면 비활성화)
   sudo tee /etc/ssh/sshd_config.d/00-franchise-security.conf > /dev/null << 'EOF'
   PasswordAuthentication no
   PubkeyAuthentication yes
   KbdInteractiveAuthentication no
   PermitRootLogin prohibit-password
   EOF
   sudo chmod 600 /etc/ssh/sshd_config.d/00-franchise-security.conf

   # 1) SSH 설정 구문 검사
   sudo sshd -t || { echo "[ERROR] SSH 구문 오류 발생!"; exit 1; }

   # 2) [필수] OpenSSH 유효 런타임 인증 정책 검증 (First-match 결과 passwordauthentication no 실증)
   # sshd -t와 키 접속 성공만으로는 타 설정 선점 여부를 알 수 없으므로 sshd -T로 실제 적용 정책을 전수 대조합니다.
   sudo sshd -T | grep -iE '^(passwordauthentication|pubkeyauthentication|permitrootlogin)'
   # 기대 출력:
   # passwordauthentication no
   # pubkeyauthentication yes
   # permitrootlogin prohibit-password

   # 3) 안전한 SSH 데몬 리로드
   sudo systemctl reload sshd || sudo systemctl reload ssh

   # [중요] 기존 터미널을 닫지 않은 채 별도 새 터미널 창을 열어 키 접속 정상 작동 확인:
   # ssh -i <SSH_PRIVATE_KEY_PATH> -p <SSH_PORT> <SSH_USER>@<SERVER_PUBLIC_IP>
   ```
3. **UFW(Uncomplicated Firewall) 방화벽 설정 (복수 관리자 IP 순회 등록)**:
   ```bash
   # 1) UFW 패키지 사전 설치 확인 및 미설치 시 즉시 설치 (최초 방화벽 설정 전 필수 종속성 확보)
   which ufw >/dev/null 2>&1 || {
       echo "[INFO] UFW 패키지가 설치되어 있지 않아 설치를 진행합니다..."
       sudo apt-get update -y && sudo apt-get install -y ufw || {
           echo "[ERROR] UFW 패키지 설치 실패! 방화벽 설정 전 단계에서 즉시 중단합니다."; exit 1;
       }
   }

   # 2) 기본 정책 설정
   sudo ufw default deny incoming
   sudo ufw default allow outgoing

   # 3) 기존 전체 공개 SSH 규칙(ALLOW/LIMIT, Anywhere / Anywhere (v6)) 충돌 제거 (관리자 IP 제한 무력화 방지)
   echo "[INFO] 기존 전체 공개 SSH 규칙 확인 및 충돌 제거..."
   sudo ufw delete allow 22/tcp 2>/dev/null || true
   sudo ufw delete allow 22 2>/dev/null || true
   sudo ufw delete allow OpenSSH 2>/dev/null || true
   sudo ufw delete limit 22/tcp 2>/dev/null || true
   sudo ufw delete limit 22 2>/dev/null || true
   sudo ufw delete limit OpenSSH 2>/dev/null || true
   if [ "<SSH_PORT>" != "22" ]; then
       sudo ufw delete allow <SSH_PORT>/tcp 2>/dev/null || true
       sudo ufw delete allow <SSH_PORT> 2>/dev/null || true
       sudo ufw delete limit <SSH_PORT>/tcp 2>/dev/null || true
       sudo ufw delete limit <SSH_PORT> 2>/dev/null || true
   fi

   # 4) 쉼표(,)로 구분된 복수 관리자 IP/CIDR 대역 순회 등록
   IFS=',' read -ra ADDR <<< "<ALLOWED_ADMIN_IPS>"
   for ip in "${ADDR[@]}"; do
       ip_trimmed=$(echo "$ip" | xargs)
       if [ -n "$ip_trimmed" ]; then
           sudo ufw allow from "$ip_trimmed" to any port <SSH_PORT> proto tcp comment "Admin SSH: $ip_trimmed"
       fi
   done

   # 5) 웹 서비스 포트 오픈
   sudo ufw allow 80/tcp comment 'HTTP / ACME Challenge'
   sudo ufw allow 443/tcp comment 'HTTPS'

   # 6) 방화벽 활성화 및 최종 정책 실증 검증 (Anywhere SSH 포트에 대한 ALLOW/LIMIT 및 IPv6 전수 부재 확인)
   sudo ufw --force enable
   sudo ufw status verbose
   if sudo ufw status verbose | grep -E "(<SSH_PORT>|22)(/tcp)?\s+(ALLOW|LIMIT)\s+IN\s+Anywhere" >/dev/null 2>&1; then
       echo "❌ [ERROR] 전체 공개(Anywhere / ALLOW 또는 LIMIT) SSH 허용 규칙(<SSH_PORT> 또는 22)이 여전히 존재합니다! 배포를 즉시 중단합니다." >&2
       exit 1
   fi

   # 별도 터미널에서 신규 SSH 세션 진입 가능 여부 최종 실증:
   # ssh -i <SSH_PRIVATE_KEY_PATH> -p <SSH_PORT> <SSH_USER>@<SERVER_PUBLIC_IP>
   ```

### Phase 2: 필수 패키지 설치 및 격리 사용자/디렉터리 생성
1. **OS 패키지 업데이트 및 필수 도구 설치 (`sqlite3`, `logrotate`, `rsync`, `nodejs 20.x`)**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3 python3-pip python3-venv git curl ufw nginx certbot python3-certbot-nginx sqlite3 logrotate rsync

   # Node.js 20.x LTS 공식 레포지토리 등록 및 설치
   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
   sudo apt install -y nodejs
   node --version && npm --version
   ```
2. **서비스 전용 시스템 계정 생성**:
   ```bash
   # 로그인 불가능한 시스템 계정 생성
   id -u franchise &>/dev/null || sudo useradd -r -s /usr/sbin/nologin -d /opt/franchise-dashboard -m franchise
   ```
3. **디렉터리 구조 생성 및 권한 설정 (지정된 `<BACKUP_DESTINATION>` 적용)**:
   ```bash
   sudo mkdir -p /opt/franchise-dashboard/data
   sudo mkdir -p <BACKUP_DESTINATION>
   sudo mkdir -p /var/log/franchise-dashboard
   sudo mkdir -p /var/www/certbot

   # 소유권 및 권한 격리
   sudo chown -R franchise:franchise /opt/franchise-dashboard
   sudo chown -R franchise:franchise <BACKUP_DESTINATION>
   sudo chown -R franchise:franchise /var/log/franchise-dashboard
   sudo chmod 755 /opt/franchise-dashboard
   sudo chmod 700 <BACKUP_DESTINATION>
   sudo chmod 755 /var/log/franchise-dashboard
   sudo chmod 755 /var/www/certbot

   # Nginx 계정(www-data)이 정적 자산을 읽을 수 있도록 그룹 추가
   sudo usermod -a -G franchise www-data
   ```

### Phase 3: 소스코드 및 운영 데이터베이스 3종 배치
1. **소스코드 배포 및 동기화 (임시 스테이징 -> 대상 디렉터리 안전 반영)**:
   - *로컬 개발 머신에서 rsync 배포 시*:
     ```bash
     # 로컬에서 서버의 임시 디렉터리로 1차 전송 (비밀정보 .env, DB, 빌드 산출물 dist* 및 불필요 파일 엄격 제외)
     rsync -avz \
         --exclude='.git' \
         --exclude='node_modules' \
         --exclude='.venv' \
         --exclude='.env*' \
         --exclude='*.env' \
         --exclude='__pycache__' \
         --exclude='*.pyc' \
         --exclude='reports/test_*' \
         --exclude='data/*.sqlite3*' \
         --exclude='backups/*' \
         --exclude='frontend/dist*' \
         -e "ssh -i <SSH_PRIVATE_KEY_PATH> -p <SSH_PORT>" \
         ./ <SSH_USER>@<SERVER_PUBLIC_IP>:/tmp/franchise-dashboard-source/
     ```
   - *서버 호스트에서 최종 디렉터리 동기화 및 소유권 설정*:
     ```bash
     # 0) 배포 시작 시점의 현재 활성 라이브 릴리스 경로 보존 및 스왑 플래그 초기화 (롤백 시 프론트/백엔드 버전 불일치 방지)
     sudo -u franchise mkdir -p /opt/franchise-dashboard/frontend/releases
     PRE_DEPLOY_LIVE=""
     if [ -L "/opt/franchise-dashboard/frontend/dist" ]; then
         PRE_DEPLOY_LIVE=$(readlink -f /opt/franchise-dashboard/frontend/dist 2>/dev/null || true)
     elif [ -d "/opt/franchise-dashboard/frontend/dist" ]; then
         PRE_DEPLOY_LIVE="/opt/franchise-dashboard/frontend/releases/release_legacy"
     fi
     if [ -n "${PRE_DEPLOY_LIVE}" ]; then
         echo "${PRE_DEPLOY_LIVE}" | sudo -u franchise tee /opt/franchise-dashboard/frontend/releases/deploy_start_live_release.txt > /dev/null
     else
         sudo rm -f /opt/franchise-dashboard/frontend/releases/deploy_start_live_release.txt
     fi
     sudo rm -f /opt/franchise-dashboard/frontend/releases/live_swapped_flag.txt

     # 1) 기존 배포 소스 존재 시 임시 경로에 스냅샷 백업 완성 후 안전한 원자적 교체 (이전 백업 보존 및 실패 시 원상복구/즉시 중단)
     PREV_SRC_BACKUP="/opt/franchise-dashboard-prev-source"
     TMP_SRC_BACKUP="/opt/.franchise-dashboard-prev-source.tmp"
     OLD_SRC_BACKUP="/opt/.franchise-dashboard-prev-source.old"
     if [ -d "/opt/franchise-dashboard/src" ]; then
         sudo rm -rf "$TMP_SRC_BACKUP"
         sudo mkdir -p "$TMP_SRC_BACKUP"
         # 임시 경로에 복사 수행 (data, backups, venv, node_modules, frontend/dist* 제외)
         sudo rsync -av --exclude='data' --exclude='backups' --exclude='.venv' --exclude='node_modules' --exclude='frontend/dist*' /opt/franchise-dashboard/ "$TMP_SRC_BACKUP/" || {
             echo "❌ [ERROR] 소스 스냅샷 백업 실패! 기존 복구본 보존을 위해 배포를 즉시 중단합니다." >&2
             sudo rm -rf "$TMP_SRC_BACKUP"
             exit 1
         }
        # 1) 선행 이동: 이전 백업이 있으면 OLD로 이동하되, 이동 실패 시 즉시 중단
        sudo rm -rf "$OLD_SRC_BACKUP"
        if [ -d "$PREV_SRC_BACKUP" ]; then
            sudo mv "$PREV_SRC_BACKUP" "$OLD_SRC_BACKUP" || {
                echo "❌ [ERROR] 기존 스냅샷 보존 이동(mv) 실패! 배포를 즉시 중단합니다." >&2
                sudo rm -rf "$TMP_SRC_BACKUP"
                exit 1
            }
        fi

        # 2) 목적지 경로가 완전히 비어 있는지(존재하지 않는지) 엄격 확인 (서브디렉터리 오이동 방지)
        if [ -e "$PREV_SRC_BACKUP" ]; then
            echo "❌ [ERROR] 목적지($PREV_SRC_BACKUP)가 여전히 존재하여 교체를 진행할 수 없습니다! 배포를 중단합니다." >&2
            [ -d "$OLD_SRC_BACKUP" ] && sudo mv "$OLD_SRC_BACKUP" "$PREV_SRC_BACKUP"
            sudo rm -rf "$TMP_SRC_BACKUP"
            exit 1
        fi

        # 3) 신규 스냅샷을 PREV_SRC_BACKUP으로 이동 (실패 시 OLD 복원 및 배포 중단)
        if sudo mv "$TMP_SRC_BACKUP" "$PREV_SRC_BACKUP"; then
            sudo rm -rf "$OLD_SRC_BACKUP"
            echo "[INFO] 기존 릴리스 소스 스냅샷 안전 보존 완료: $PREV_SRC_BACKUP"
        else
            echo "❌ [ERROR] 신규 스냅샷 교체(mv) 실패! 이전 백업을 원상복구하고 배포를 즉시 중단합니다." >&2
            [ -d "$OLD_SRC_BACKUP" ] && sudo mv "$OLD_SRC_BACKUP" "$PREV_SRC_BACKUP"
            exit 1
        fi
    fi

     # 2) 소스코드만 안전하게 /opt/franchise-dashboard/로 동기화 (기존 data/, backups/, frontend/dist* 제외로 운영 정적 파일 덮어쓰기 원천 방지, 실패 시 즉시 중단)
     sudo rsync -av --exclude='data' --exclude='backups' --exclude='.env*' --exclude='frontend/dist*' /tmp/franchise-dashboard-source/ /opt/franchise-dashboard/ || {
         echo "[ERROR] 운영 소스 반영(rsync) 실패! 불완전한 소스 전파를 방지하기 위해 배포를 즉시 중단합니다."
         exit 1
     }
     sudo rm -rf /tmp/franchise-dashboard-source
     sudo chown -R franchise:franchise /opt/franchise-dashboard
     sudo chmod 755 /opt/franchise-dashboard
     ```
2. **운영 데이터베이스 3종 배치 및 무결성 확인**:
   - *로컬 개발 머신에서 운영 DB 3종 전용 전송 (신규 서버 설치 또는 DB 갱신 시 수행)*:
     ```bash
     # 소스와 분리하여 DB 3종(총 약 747MB)을 서버 임시 데이터 스테이징으로 독립 전송
     rsync -avz -e "ssh -i <SSH_PRIVATE_KEY_PATH> -p <SSH_PORT>" \
         ./data/brand_master_v1.sqlite3 \
         ./data/franchise_analytics_v1.sqlite3 \
         ./data/ftc_macro_statistics_v1.sqlite3 \
         <SSH_USER>@<SERVER_PUBLIC_IP>:/tmp/franchise-dashboard-data/
     ```
   - *서버 호스트에서 DB 배치, 기존 DB 보존 및 신규 설치*:
     ```bash
    DATA_DIR="/opt/franchise-dashboard/data"
    STAGE_DIR="/tmp/franchise-dashboard-data"

    # data/ 디렉터리에 3종 DB 안전 배치 (이동 실패 시 즉시 중단 및 스테이징 보존)
    for db in brand_master_v1.sqlite3 franchise_analytics_v1.sqlite3 ftc_macro_statistics_v1.sqlite3; do
        if [ -f "$DATA_DIR/$db" ]; then
            echo "[INFO] 기존 운영 DB가 이미 존재합니다: $db (기존 DB 보존, 덮어쓰기 건너뜀)"
        else
            echo "[INFO] 신규 DB 배치 실행: $db"
            if [ -f "$STAGE_DIR/$db" ]; then
                sudo mv "$STAGE_DIR/$db" "$DATA_DIR/$db" || {
                    echo "❌ [ERROR] DB 이동(mv) 실패: $db! 스테이징을 보존하고 배포를 즉시 중단합니다." >&2
                    exit 1
                }
                [ -f "$DATA_DIR/$db" ] || {
                    echo "❌ [ERROR] 이동 후 목적지 파일 부재: $DATA_DIR/$db! 배포를 즉시 중단합니다." >&2
                    exit 1
                }
            else
                echo "❌ [ERROR] 신규 DB 배치 파일이 없습니다: $STAGE_DIR/$db" >&2
                exit 1
            fi
        fi
    done

    # 3개 DB 모두 목적지에 정상 존재하는지 최종 확인 후 스테이징 안전 정리
    for db in brand_master_v1.sqlite3 franchise_analytics_v1.sqlite3 ftc_macro_statistics_v1.sqlite3; do
        [ -f "$DATA_DIR/$db" ] || { echo "❌ [ERROR] 필수 DB 누락: $DATA_DIR/$db"; exit 1; }
    done
    sudo rm -rf "$STAGE_DIR"

    # 파일 읽기 권한 및 소유권 부여
    sudo chmod 644 "$DATA_DIR"/*.sqlite3
    sudo chown franchise:franchise "$DATA_DIR"/*.sqlite3

    # 읽기 전용 모드(-readonly)로 빈 DB 생성 차단 및 무결성·핵심 테이블·건수 전수 검증
    # 1) brand_master_v1: brands 테이블 건수 5,000건 이상
    BM_RES=$(sqlite3 -readonly "file:$DATA_DIR/brand_master_v1.sqlite3?mode=ro" "PRAGMA integrity_check; SELECT COUNT(*) FROM brands;")
    echo "$BM_RES" | grep -q "ok" || { echo "❌ [ERROR] brand_master 무결성 검사 실패!"; exit 1; }
    BM_COUNT=$(echo "$BM_RES" | tail -n 1)
    [ "$BM_COUNT" -ge 5000 ] || { echo "❌ [ERROR] brand_master brands 건수 부족 ($BM_COUNT < 5000)!"; exit 1; }
    echo "[PASS] brand_master_v1.sqlite3: 무결성 ok, brands $BM_COUNT건 확인"

    # 2) franchise_analytics_v1: quick_check 및 테이블 7개 이상
    FA_RES=$(sqlite3 -readonly "file:$DATA_DIR/franchise_analytics_v1.sqlite3?mode=ro" "PRAGMA quick_check; SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
    echo "$FA_RES" | grep -q "ok" || { echo "❌ [ERROR] franchise_analytics 무결성 검사 실패!"; exit 1; }
    FA_TABLES=$(echo "$FA_RES" | tail -n 1)
    [ "$FA_TABLES" -ge 7 ] || { echo "❌ [ERROR] franchise_analytics 테이블 수 부족 ($FA_TABLES < 7)!"; exit 1; }
    echo "[PASS] franchise_analytics_v1.sqlite3: 무결성 ok, 테이블 $FA_TABLES개 확인"

    # 3) ftc_macro_statistics_v1: integrity_check 및 ftc_industry_macro_summary 건수 존재
    MC_RES=$(sqlite3 -readonly "file:$DATA_DIR/ftc_macro_statistics_v1.sqlite3?mode=ro" "PRAGMA integrity_check; SELECT COUNT(*) FROM ftc_industry_macro_summary;")
    echo "$MC_RES" | grep -q "ok" || { echo "❌ [ERROR] ftc_macro_statistics 무결성 검사 실패!"; exit 1; }
    MC_COUNT=$(echo "$MC_RES" | tail -n 1)
    [ "$MC_COUNT" -gt 0 ] || { echo "❌ [ERROR] ftc_macro_statistics 건수 부족 ($MC_COUNT <= 0)!"; exit 1; }
    echo "[PASS] ftc_macro_statistics_v1.sqlite3: 무결성 ok, ftc_industry_macro_summary $MC_COUNT건 확인"
     ```

### Phase 4: Python 3.12 가상환경 및 백엔드 의존성 구성
1. **가상환경 생성 및 패키지 설치**:
   ```bash
   cd /opt/franchise-dashboard
   sudo -u franchise python3 -m venv .venv
   sudo -u franchise /opt/franchise-dashboard/.venv/bin/pip install --upgrade pip
   sudo -u franchise /opt/franchise-dashboard/.venv/bin/pip install -r requirements.txt
   ```
2. **프로덕션 환경변수 파일 생성 및 보존 (`.env.production`)**:
   ```bash
   # 최초 설치 시에만 템플릿으로부터 .env.production을 생성하고, 재배포 시에는 기존 운영 설정을 안전하게 보존
   if [ ! -f .env.production ]; then
       echo "[INFO] 최초 설치: .env.production 파일 생성..."
       sudo -u franchise cp deploy/env.production.example .env.production
       # 환경변수 설정: ENVIRONMENT=production, OPERATING_DOMAIN 설정
       sudo -u franchise sed -i "s/dashboard.example.com/<OPERATING_DOMAIN>/g" .env.production
       sudo chmod 600 .env.production
   else
       echo "[INFO] 기존 .env.production 파일이 이미 존재하므로 기존 운영 설정을 안전하게 보존합니다."
       if ! grep -q "<OPERATING_DOMAIN>" .env.production; then
           echo "[WARN] 기존 .env.production에 <OPERATING_DOMAIN>이 누락되었는지 확인하십시오."
       fi
   fi
   ```

### Phase 5: 프론트엔드 동일 출처 프로덕션 빌드 및 정적 파일 원자적 배치
서비스 중인 Nginx 정적 서빙 디렉터리(`frontend/dist`)에서 직접 빌드를 수행하거나 디렉터리를 삭제/이동 후 재생성하면 두 명령 사이에 서빙 경로가 사라져 404 Not Found 또는 정적 자산 누락 구간이 발생합니다.
따라서 타임스탬프 기반 독립 릴리스 디렉터리(`releases/release_${BUILD_TS}`)에 빌드를 완수하고 검증한 후, Linux 커널의 단일 원자적 rename 시스템 콜(`mv -Tf`)을 통한 **원자적 심볼릭 링크 스왑(Atomic Symlink Swap)**을 수행합니다. 심볼릭 링크 체계 간 전환 시에는 단일 rename으로 경로 소멸 구간 0나노초의 무중단 전환을 달성하며, 레거시 일반 디렉터리에서 최초 전환하는 1회에 한해서는 미세한 전환 구간이 발생할 수 있으므로 실패 시 기존 일반 디렉터리 원상복구 방어벽을 구비합니다:

1. **프론트엔드 의존성 설치 및 독립 릴리스 프로덕션 빌드**:
   ```bash
   cd /opt/franchise-dashboard/frontend
   sudo -u franchise npm ci
   
   # 고유 타임스탬프 릴리스 디렉터리 생성 및 빌드 (서비스 중인 기존 릴리스에 0% 영향)
   BUILD_TS=$(date +%Y%m%d_%H%M%S)
   RELEASE_DIR="/opt/franchise-dashboard/frontend/releases/release_${BUILD_TS}"
   sudo -u franchise mkdir -p /opt/franchise-dashboard/frontend/releases
   sudo -u franchise npm run build -- --outDir "releases/release_${BUILD_TS}"
   ```
2. **빌드 무결성 사전 검증 및 원자적 심볼릭 링크 전환 (Atomic Symlink Swap)**:
   ```bash
   # 1) 빌드 필수 자산(index.html, JS/CSS 번들) 검증 (실패 시 기존 서빙 100% 보존 및 즉시 중단)
   if [ ! -f "${RELEASE_DIR}/index.html" ] || [ ! -d "${RELEASE_DIR}/assets" ]; then
       echo "[ERROR] 새 릴리스 빌드 결과물(index.html, assets)이 누락되었습니다. 기존 서빙을 유지하고 전환을 중단합니다."
       exit 1
   fi

   # 2) 파일 권한 부여
   sudo chmod -R 755 "${RELEASE_DIR}"

   # 3) 전환 직전 현재 서빙 중인 실제 경로를 이전 정상 릴리스 기준점으로 안전하게 보존
   if [ -L "/opt/franchise-dashboard/frontend/dist" ]; then
       PREV_LIVE_TARGET=$(readlink -f /opt/franchise-dashboard/frontend/dist 2>/dev/null || true)
   elif [ -d "/opt/franchise-dashboard/frontend/dist" ]; then
       # 기존 dist가 심볼릭 링크가 아닌 일반 디렉터리인 경우 백업될 위치로 지정
       PREV_LIVE_TARGET="/opt/franchise-dashboard/frontend/releases/release_legacy"
   else
       PREV_LIVE_TARGET=""
   fi
   if [ -n "${PREV_LIVE_TARGET}" ]; then
       echo "${PREV_LIVE_TARGET}" | sudo -u franchise tee /opt/franchise-dashboard/frontend/releases/previous_live_release.txt > /dev/null
   fi

    # 4) 이전 릴리스의 해시 정적 에셋(assets/*)을 신규 릴리스에 비파괴적 병합 (구버전 HTML을 수신한 클라이언트의 후속 chunk 404 원천 방지)
    if [ -d "/opt/franchise-dashboard/frontend/dist/assets" ]; then
        echo "[INFO] 이전 릴리스의 정적 에셋을 신규 릴리스에 비파괴 병합(cp -n)하여 전환 중 구버전 사용자의 404를 방지합니다."
        sudo -u franchise cp -n /opt/franchise-dashboard/frontend/dist/assets/* "${RELEASE_DIR}/assets/" || {
           echo "❌ [ERROR] 이전 릴리스 정적 에셋 병합 실패! 구버전 사용자 404 방지를 위해 배포를 즉시 중단합니다." >&2
           exit 1
       }
    fi

   # 5) franchise 권한으로 임시 심볼릭 링크(dist.tmp)를 먼저 생성 및 검증 (실패 시 배포 즉시 중단 및 기존 서빙 100% 보존)
   sudo -u franchise ln -sfn "${RELEASE_DIR}" /opt/franchise-dashboard/frontend/dist.tmp || {
       echo "❌ [ERROR] 임시 심볼릭 링크 생성 실패! 기존 서빙을 유지하고 배포를 즉시 중단합니다." >&2
       exit 1
   }

   # 6) 최초 1회 처리: 기존 dist가 심볼릭 링크가 아닌 일반 디렉터리인 경우 레거시 디렉터리로 안전하게 백업 전환 (실패 시 즉시 중단)
   # (참고: 일반 디렉터리에서 심볼릭 링크로의 최초 전환 시에는 미세한 경로 전환 구간이 발생할 수 있으며, 전환 실패 시 기존 일반 디렉터리 자동 원상복구)
   LEGACY_DIST_DIR=""
   if [ -d "/opt/franchise-dashboard/frontend/dist" ] && [ ! -L "/opt/franchise-dashboard/frontend/dist" ]; then
       LEGACY_DIST_DIR="/opt/franchise-dashboard/frontend/releases/release_legacy"
       sudo rm -rf "${LEGACY_DIST_DIR}"
       sudo mv /opt/franchise-dashboard/frontend/dist "${LEGACY_DIST_DIR}" || {
           echo "❌ [ERROR] 기존 디렉터리 백업 이동 실패! 배포를 즉시 중단합니다." >&2
           sudo rm -f /opt/franchise-dashboard/frontend/dist.tmp
           exit 1
       }
   fi

   # 7) POSIX rename 원자적 심볼릭 링크 교체 (심볼릭 링크 간 전환 시 경로 소멸 0나노초 무중단 전환, 실패 시 즉시 원상복구 및 중단)
   if sudo mv -Tf /opt/franchise-dashboard/frontend/dist.tmp /opt/franchise-dashboard/frontend/dist; then
       echo "[INFO] 검증된 신규 릴리스(${RELEASE_DIR})로 정적 서빙 원자적 심볼릭 링크 전환 완료"
       echo "1" | sudo -u franchise tee /opt/franchise-dashboard/frontend/releases/live_swapped_flag.txt > /dev/null
   else
       echo "❌ [ERROR] 정적 서빙 심볼릭 링크 원자적 교체 실패! 기존 상태를 원상복구합니다." >&2
       if [ -n "${LEGACY_DIST_DIR}" ] && [ -d "${LEGACY_DIST_DIR}" ] && [ ! -e "/opt/franchise-dashboard/frontend/dist" ]; then
           sudo mv "${LEGACY_DIST_DIR}" /opt/franchise-dashboard/frontend/dist
           echo "[INFO] 기존 일반 디렉터리(${LEGACY_DIST_DIR})로 서빙 경로를 원상복구했습니다."
       fi
       exit 1
   fi
   ```

### Phase 6: systemd 서비스 유닛 등록 및 백엔드 데몬 가동
1. **서비스 유닛 복사 및 데몬 리로드**:
   ```bash
   sudo cp /opt/franchise-dashboard/deploy/franchise-dashboard.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable franchise-dashboard
   # 최초 배포 시 가동 및 재배포 시 기존 실행 중인 백엔드 프로세스를 새 코드로 확실하게 전환하기 위해 restart 수행
   sudo systemctl restart franchise-dashboard
   ```
2. **백엔드 데몬 상태 및 로컬 응답 확인**:
   ```bash
   sudo systemctl status franchise-dashboard --no-pager
   curl -f http://127.0.0.1:8000/api/health
   # 반환: {"status":"healthy", "total_stores_universe":735185, ...}
   ```

### Phase 7: Nginx 2단계 TLS 프로비저닝 및 리버스 프록시 가동
신규 서버에는 Let's Encrypt 인증서가 아직 없으므로, 반드시 2단계 부트스트랩 순서를 따른다:

1. **[Step 7-1: 초기 HTTP 부트스트랩 활성화]**:
   ```bash
   sudo cp /opt/franchise-dashboard/deploy/nginx-bootstrap.conf /etc/nginx/sites-available/franchise-dashboard-bootstrap.conf
   sudo sed -i 's/dashboard.example.com/<OPERATING_DOMAIN>/g' /etc/nginx/sites-available/franchise-dashboard-bootstrap.conf
   sudo ln -sf /etc/nginx/sites-available/franchise-dashboard-bootstrap.conf /etc/nginx/sites-enabled/
   sudo rm -f /etc/nginx/sites-enabled/default
   sudo nginx -t && sudo systemctl reload nginx
   ```
2. **[Step 7-2: Certbot Webroot 발급 및 자동 갱신 리로드 훅 등록]**:
   ```bash
   sudo certbot certonly --webroot -w /var/www/certbot \
       -d <OPERATING_DOMAIN> \
       --non-interactive --agree-tos \
       -m <ADMIN_EMAIL> \
       --deploy-hook "systemctl reload nginx"

   # 갱신 드라이런 테스트로 훅 작동 검증
   sudo certbot renew --dry-run
   ```
3. **[Step 7-3: 메인 HTTPS 설정 전환 및 정식 가동]**:
   ```bash
   sudo cp /opt/franchise-dashboard/deploy/nginx.conf /etc/nginx/sites-available/franchise-dashboard.conf
   sudo sed -i 's/dashboard.example.com/<OPERATING_DOMAIN>/g' /etc/nginx/sites-available/franchise-dashboard.conf
   sudo ln -sf /etc/nginx/sites-available/franchise-dashboard.conf /etc/nginx/sites-enabled/
   sudo rm -f /etc/nginx/sites-enabled/franchise-dashboard-bootstrap.conf
   sudo nginx -t && sudo systemctl reload nginx
   ```

### Phase 8: 운영 자동화 등록 (일일 백업 cron 및 로그 관리)
1. **일일 백업 cron 등록 (매일 새벽 03:00, 지정된 파라미터 적용)**:
   ```bash
   echo "0 3 * * * franchise /opt/franchise-dashboard/.venv/bin/python /opt/franchise-dashboard/scripts/backup_production_db.py --target-dir <BACKUP_DESTINATION> --retention-days <BACKUP_RETENTION_DAYS> >> /var/log/franchise-dashboard/backup.log 2>&1" | sudo tee /etc/cron.d/franchise-backup
   sudo chmod 644 /etc/cron.d/franchise-backup
   ```
2. **백업 로그 로테이션(Logrotate) 등록 및 드라이런 검증**:
   ```bash
   sudo tee /etc/logrotate.d/franchise-backup > /dev/null << 'EOF'
   /var/log/franchise-dashboard/*.log {
       weekly
       rotate 4
       missingok
       notifempty
       compress
       delaycompress
       create 0644 franchise franchise
   }
   EOF
   sudo chmod 644 /etc/logrotate.d/franchise-backup

   # Logrotate 드라이런 검증
   sudo logrotate -d /etc/logrotate.d/franchise-backup
   ```
3. **지정 경로에 수동 1회 백업 실행 검증**:
   ```bash
   sudo -u franchise /opt/franchise-dashboard/.venv/bin/python /opt/franchise-dashboard/scripts/backup_production_db.py --target-dir <BACKUP_DESTINATION> --retention-days <BACKUP_RETENTION_DAYS>
   sudo ls -lh <BACKUP_DESTINATION>
   ```

---

## 5. 배포 직후 검증 시나리오 (Verification Scenarios)

배포 직후 아래 6개 검증 항목을 모두 수행하여 정상 여부를 판정한다:

| 검증 ID | 대상 | 실행 명령어 | 기대 결과 (PASS 기준) |
|:---:|:---|:---|:---|
| **V-01** | 백엔드 데몬 | `curl -f http://127.0.0.1:8000/api/health` | HTTP 200, status=healthy, total_stores_universe=735185 반환 |
| **V-02** | 리버스 프록시 헬스체크 | `curl -f -k https://<OPERATING_DOMAIN>/healthz` | HTTP 200, 백엔드 헬스체크 데이터 동일 출력 |
| **V-03** | 프론트엔드 정적 서빙 | `curl -I https://<OPERATING_DOMAIN>/` | HTTP 200, content-type: text/html, 보안 헤더 4종 포함 |
| **V-04** | 동일 출처 API 프록시 | `curl -s https://<OPERATING_DOMAIN>/api/v1/analytics/summary` | HTTP 200, 유효 JSON 객체 반환 (SPA fallback HTML 아님) |
| **V-05** | 정적 자산 캐싱 헤더 | `ASSET_JS=$(ls -1 /opt/franchise-dashboard/frontend/dist/assets/index-*.js 2>/dev/null \| head -n 1 \| xargs -I {} basename {}); curl -I "https://<OPERATING_DOMAIN>/assets/${ASSET_JS}"` | HTTP 200, cache-control: public, max-age=31536000, immutable |
| **V-06** | 백업 무결성 파일 | `sudo ls -la <BACKUP_DESTINATION>` | 3개 DB 백업 파일, .sha256, .meta.json 생성 완료 |

---

## 6. 장애 대응 및 롤백 절차 (Rollback Plan)

배포 중 또는 배포 직후 심각한 결함 발생 시 영향도에 따라 3단계 롤백 절차를 적용한다:

```
[ 장애 발생 감지 ]
       │
       ├─ [Level 1: 프로세스 오류] ─► systemctl restart franchise-dashboard & journalctl 확인
       │
       ├─ [Level 2: Nginx/TLS 오류] ─► nginx-bootstrap.conf 재연결 또는 백업 conf 복원
       │
       └─ [Level 3: DB/전체 장애] ─► 백업 디렉터리 이동 -> 개별 최신 백업 탐색 -> 체크섬 검증 -> 동일 파일시스템 스테이징 무결성 검사 -> 원자적 rename 교체
```

### 6.1 Level 1: FastAPI 백엔드 프로세스 오류
- **현상**: `/healthz` 또는 `/api/` 요청 시 502 Bad Gateway 발생
- **조치 절차**:
  1. 서비스 상태 및 최근 로그 확인:
     ```bash
     sudo systemctl status franchise-dashboard
     sudo journalctl -u franchise-dashboard -n 50 --no-pager
     ```
  2. 프로세스 재시작:
     ```bash
     sudo systemctl restart franchise-dashboard
     ```
  3. 문제 지속 시 직전 소스 스냅샷(/opt/franchise-dashboard-prev-source)으로 롤백 및 재기동:
     ```bash
     if [ -d "/opt/franchise-dashboard-prev-source/src" ]; then
         echo "[ROLLBACK] 직전 소스 스냅샷(/opt/franchise-dashboard-prev-source)으로 복원을 시작합니다..."
         sudo systemctl stop franchise-dashboard

         # 영속 data, backups, venv, .env*, frontend/dist*, frontend/releases*는 보존하고 소스 파일만 안전하게 복원 (신규 추가 파일 제거를 위한 --delete 적용, 실패 시 즉시 중단)
         # BACKUP_DESTINATION이 /opt/franchise-dashboard 하위에 위치할 경우 해당 경로를 동적으로 제외하여 백업 삭제 방지
         RAW_BACKUP_DEST="<BACKUP_DESTINATION>"
         BACKUP_EXCLUDE_ARG=""
         case "$RAW_BACKUP_DEST" in
             /opt/franchise-dashboard/*)
                 REL_BACKUP_PATH="${RAW_BACKUP_DEST#/opt/franchise-dashboard/}"
                 BACKUP_EXCLUDE_ARG="--exclude=${REL_BACKUP_PATH}*"
                 ;;
         esac

         sudo rsync -av --delete \
             --exclude='data' \
             --exclude='backups' \
             --exclude='backups*' \
             ${BACKUP_EXCLUDE_ARG:+"$BACKUP_EXCLUDE_ARG"} \
             --exclude='.venv' \
             --exclude='.env*' \
             --exclude='frontend/dist*' \
             --exclude='frontend/releases*' \
             /opt/franchise-dashboard-prev-source/ /opt/franchise-dashboard/ || {
             echo "[ERROR] 이전 소스 복원(rsync) 실패! 불완전한 소스 상태에서 기동을 방지하기 위해 롤백을 즉시 중단합니다."
             exit 1
         }
         sudo chown -R franchise:franchise /opt/franchise-dashboard

        # 프론트엔드 정적 서빙 롤백: 이번 배포에서 심볼릭 링크가 스왑된 경우에만 롤백
        # (Phase 3~4에서 실패한 경우 기존 프론트엔드 서빙 경로를 안전하게 유지하여 백엔드/프론트엔드 버전 불일치 방지)
        if [ -f "/opt/franchise-dashboard/frontend/releases/live_swapped_flag.txt" ]; then
            PREV_REL=""
            # 1) 배포 시작 시점의 라이브 릴리스 기록 확인 및 유효 디렉터리 검증
            if [ -f "/opt/franchise-dashboard/frontend/releases/deploy_start_live_release.txt" ]; then
                CANDIDATE=$(cat /opt/franchise-dashboard/frontend/releases/deploy_start_live_release.txt | tr -d '[:space:]')
                if [ -n "$CANDIDATE" ] && [ -d "$CANDIDATE" ]; then
                    PREV_REL="$CANDIDATE"
                fi
            fi
            # 2) 시작 기록이 없거나 유효하지 않은 경우 전환 직전 정상 릴리스 기록(previous_live_release.txt) 확인
            if [ -z "$PREV_REL" ] && [ -f "/opt/franchise-dashboard/frontend/releases/previous_live_release.txt" ]; then
                CANDIDATE=$(cat /opt/franchise-dashboard/frontend/releases/previous_live_release.txt | tr -d '[:space:]')
                if [ -n "$CANDIDATE" ] && [ -d "$CANDIDATE" ]; then
                    PREV_REL="$CANDIDATE"
                fi
            fi
            if [ -n "$PREV_REL" ] && [ -f "${PREV_REL}/index.html" ]; then
                # 롤백 직전에 새 버전 HTML을 내려받은 사용자가 롤백 후 후속 chunk(JS/CSS) 요청 시 404가 발생하지 않도록,
                # 현재 서비스 중인 릴리스의 해시 정적 에셋(dist/assets/*)을 복원 대상 릴리스(${PREV_REL}/assets/)에 비파괴 병합
                if [ -d "/opt/franchise-dashboard/frontend/dist/assets" ] && [ -d "${PREV_REL}/assets" ]; then
                    echo "[INFO] 롤백 전 페이지 사용자의 404를 방지하기 위해 현재 릴리스 에셋을 복원 대상에 비파괴 병합(cp -n)합니다."
                    sudo -u franchise cp -n /opt/franchise-dashboard/frontend/dist/assets/* "${PREV_REL}/assets/" || {
                        echo "❌ [ERROR] 롤백 정적 자산 보존(cp -n) 실패! 롤백 플래그를 보존하고 배포를 즉시 중단합니다." >&2
                        exit 1
                    }
                fi

                echo "[INFO] 배포 시작 시점의 라이브 릴리스(${PREV_REL})로 정적 서빙 심볼릭 링크를 원자적으로 즉시 복원합니다."
                sudo -u franchise ln -sfn "${PREV_REL}" /opt/franchise-dashboard/frontend/dist.tmp || {
                    echo "❌ [ERROR] 롤백 임시 심볼릭 링크 생성 실패! 롤백 플래그를 보존하고 배포를 즉시 중단합니다." >&2
                    exit 1
                }
                sudo mv -Tf /opt/franchise-dashboard/frontend/dist.tmp /opt/franchise-dashboard/frontend/dist || {
                    echo "❌ [ERROR] 롤백 심볼릭 링크 원자적 교체(mv -Tf) 실패! 롤백 플래그를 보존하고 배포를 즉시 중단합니다." >&2
                    exit 1
                }
                echo "[INFO] 정적 서빙 심볼릭 링크 복원 완료: /opt/franchise-dashboard/frontend/dist -> ${PREV_REL}"
                sudo rm -f /opt/franchise-dashboard/frontend/releases/live_swapped_flag.txt
            else
                echo "❌ [ERROR] 복원 대상 라이브 릴리스(${PREV_REL}) 또는 index.html을 찾을 수 없습니다! 롤백 플래그를 보존하고 즉시 중단합니다." >&2
                exit 1
            fi
        else
            echo "[INFO] 이번 배포에서 프론트엔드 심볼릭 링크가 스왑되지 않았으므로 기존 정적 서빙 경로를 온전히 유지합니다."
        fi

         # 백엔드 및 프론트엔드 의존성 완전 복원 (이전 package-lock.json 기준 npm ci) 및 검증 (실패 시 즉시 중단 및 서비스 기동 차단)
         sudo -u franchise bash -c '
             set -e
             cd /opt/franchise-dashboard
             .venv/bin/pip install -r requirements.txt
             npm --prefix frontend ci
         ' || {
             echo "[ERROR] 롤백 의존성(Python/Node) 설치 실패! 비정상 상태 기동을 방지하기 위해 서비스를 시작하지 않고 즉시 중단합니다."
             exit 1
         }

         # 복원 및 빌드 성공 확인 후 서비스 재기동 (배포 시간대 내 신속 재기동)
         sudo systemctl restart franchise-dashboard
         echo "[INFO] 백엔드 프로세스 준비 상태 검사 (최대 15초 폴링)..."
         HEALTH_OK=0
         for i in {1..15}; do
             if curl -sSf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
                 HEALTH_OK=1
                 break
             fi
             sleep 1
         done
         if [ "$HEALTH_OK" -eq 1 ]; then
             echo "[PASS] 롤백 후 헬스체크 성공 (${i}초 소요)"
         else
             echo "❌ [ERROR] 롤백 후 헬스체크 실패 (15초 초과)! journalctl 로그를 확인하십시오." >&2
             sudo journalctl -u franchise-dashboard -n 30 --no-pager
             exit 1
         fi
         echo "[SUCCESS] 직전 안정 릴리스 소스로 롤백 및 정상 기동 완료"
     else
         echo "[ERROR] 직전 소스 스냅샷(/opt/franchise-dashboard-prev-source)이 존재하지 않습니다."
     fi
     ```

### 6.2 Level 2: Nginx 리버스 프록시 또는 TLS 인증서 오류
- **현상**: HTTPS 접속 실패, SSL 핸드셰이크 오류, Nginx 설정 오류(`nginx -t` 실패)
- **조치 절차**:
  1. Nginx 문법 검사:
     ```bash
     sudo nginx -t
     ```
  2. 필요 시 초기 HTTP 부트스트랩 설정으로 신속 롤백하여 안내 페이지 유지:
     ```bash
     sudo ln -sf /etc/nginx/sites-available/franchise-dashboard-bootstrap.conf /etc/nginx/sites-enabled/franchise-dashboard.conf
     sudo systemctl reload nginx
     ```
  3. 인증서 경로(`/etc/letsencrypt/live/<OPERATING_DOMAIN>/`) 권한 및 파일 존재 여부 재확인.

### 6.3 Level 3: 서비스 데이터베이스 오류 또는 파일 손상 (안전한 원자적 복구)
- **현상**: DB 쿼리 시 SQLite 디스크 I/O 오류, corrupted 오류 발생
- **원자적 복구 6단계 절차 (권한 있는 동일 셸 `sudo bash` 내 실행)**:
  1. **서비스 일시 중단**:
     ```bash
     sudo systemctl stop franchise-dashboard
     ```
  2. **권한 있는 동일 셸(`sudo bash`) 내 백업 디렉터리 이동, 탐색, 무결성 검증, 안전한 원자적 교체 실행**:
     ```bash
     # 백업 디렉터리(권한 700) 접근 및 작업 전체를 권한 있는 동일 셸(sudo bash)에서 일관되게 수행
     sudo bash -c '
     set -e
     cd <BACKUP_DESTINATION> || { echo "백업 디렉터리 접근 실패!"; exit 1; }

     # 3개 DB 최신 백업 파일 개별 탐색 (초 경계 불일치 방지)
     RESTORE_BRAND=$(ls -1t brand_master_v1_backup_*.sqlite3 2>/dev/null | head -n 1)
     RESTORE_ANALYTICS=$(ls -1t franchise_analytics_v1_backup_*.sqlite3 2>/dev/null | head -n 1)
     RESTORE_MACRO=$(ls -1t ftc_macro_statistics_v1_backup_*.sqlite3 2>/dev/null | head -n 1)

     echo "복원 대상: $RESTORE_BRAND, $RESTORE_ANALYTICS, $RESTORE_MACRO"
     if [ -z "$RESTORE_BRAND" ] || [ -z "$RESTORE_ANALYTICS" ] || [ -z "$RESTORE_MACRO" ]; then
         echo "필수 백업 파일 중 일부를 찾을 수 없습니다! 복원 중단"; exit 1
     fi

     # 체크섬 개별 사전 검증 (백업 디렉터리 내 상대 경로 기준 검증, 1차 안전장치)
     sha256sum -c "${RESTORE_BRAND}.sha256" || { echo "brand_master 체크섬 검증 실패!"; exit 1; }
     sha256sum -c "${RESTORE_ANALYTICS}.sha256" || { echo "franchise_analytics 체크섬 검증 실패!"; exit 1; }
     sha256sum -c "${RESTORE_MACRO}.sha256" || { echo "ftc_macro 체크섬 검증 실패!"; exit 1; }

     # 동일 파일시스템 내 스테이징 복사 및 SQLite 무결성 전수 검사 (2차 안전장치)
     STAGING_DIR="/opt/franchise-dashboard/data/.restore_staging"
     rm -rf "$STAGING_DIR" && mkdir -p "$STAGING_DIR"
     cp "$RESTORE_BRAND" "$STAGING_DIR/brand_master_v1.sqlite3"
     cp "$RESTORE_ANALYTICS" "$STAGING_DIR/franchise_analytics_v1.sqlite3"
     cp "$RESTORE_MACRO" "$STAGING_DIR/ftc_macro_statistics_v1.sqlite3"

     sqlite3 "$STAGING_DIR/brand_master_v1.sqlite3" "PRAGMA integrity_check;" | grep -q "ok" || { echo "brand_master 무결성 오류!"; exit 1; }
     sqlite3 "$STAGING_DIR/franchise_analytics_v1.sqlite3" "PRAGMA integrity_check;" | grep -q "ok" || { echo "franchise_analytics 무결성 오류!"; exit 1; }
     sqlite3 "$STAGING_DIR/ftc_macro_statistics_v1.sqlite3" "PRAGMA integrity_check;" | grep -q "ok" || { echo "ftc_macro 무결성 오류!"; exit 1; }

     # 5. 동일 파일시스템 안전한 원자적 교체 및 실패 시 원상복구(Rollback)
     DATA_DIR="/opt/franchise-dashboard/data"
     RESTORE_TS=$(date +%Y%m%d_%H%M%S)
     CUR_BAK_DIR="$DATA_DIR/.prev_backup_${RESTORE_TS}"

     # 이번 복구 실행 고유 백업 디렉터리 생성 (과거 잔여 파일 오복원 방지)
     mkdir -p "$CUR_BAK_DIR"

     # 복구 실패 시 이번 실행에서 이동한 DB만 정확히 원상복구하는 함수 (복원 100% 성공 시에만 정리, 실패 시 백업 보존)
     rollback_swap() {
         echo "❌ [ERROR] DB 교체 실패! 이번 실행에서 백업한 기존 DB를 원상복구합니다." >&2
         local restore_failed=0
         if [ -f "$CUR_BAK_DIR/brand_master_v1.sqlite3" ]; then
             mv -f "$CUR_BAK_DIR/brand_master_v1.sqlite3" "$DATA_DIR/brand_master_v1.sqlite3" || restore_failed=1
         fi
         if [ -f "$CUR_BAK_DIR/franchise_analytics_v1.sqlite3" ]; then
             mv -f "$CUR_BAK_DIR/franchise_analytics_v1.sqlite3" "$DATA_DIR/franchise_analytics_v1.sqlite3" || restore_failed=1
         fi
         if [ -f "$CUR_BAK_DIR/ftc_macro_statistics_v1.sqlite3" ]; then
             mv -f "$CUR_BAK_DIR/ftc_macro_statistics_v1.sqlite3" "$DATA_DIR/ftc_macro_statistics_v1.sqlite3" || restore_failed=1
         fi

         if [ "$restore_failed" -eq 0 ]; then
             rm -rf "$CUR_BAK_DIR"
             echo "[INFO] 기존 DB 원상복구 완료. 임시 백업 디렉터리를 정리했습니다."
         else
             echo "❌ [CRITICAL] 원상복구 중 mv 실패! 데이터 안전 보존을 위해 백업 디렉터리($CUR_BAK_DIR)를 보존합니다." >&2
         fi
         echo "[INFO] 검증된 복구 스테이징 디렉터리($STAGING_DIR)는 전혀 손상되지 않고 안전하게 보존되었습니다."
         exit 1
     }

     # 스테이징 원본을 보존하면서 동일 파일시스템 내 교체용 임시 파일(.new) 생성
     cp -p "$STAGING_DIR/brand_master_v1.sqlite3" "$DATA_DIR/brand_master_v1.sqlite3.new" || rollback_swap
     cp -p "$STAGING_DIR/franchise_analytics_v1.sqlite3" "$DATA_DIR/franchise_analytics_v1.sqlite3.new" || rollback_swap
     cp -p "$STAGING_DIR/ftc_macro_statistics_v1.sqlite3" "$DATA_DIR/ftc_macro_statistics_v1.sqlite3.new" || rollback_swap

     # 기존 운영 DB를 이번 실행 고유 백업 디렉터리로 안전 이동 (실패 시 즉시 원상복구)
     [ -f "$DATA_DIR/brand_master_v1.sqlite3" ] && { mv -f "$DATA_DIR/brand_master_v1.sqlite3" "$CUR_BAK_DIR/brand_master_v1.sqlite3" || rollback_swap; }
     [ -f "$DATA_DIR/franchise_analytics_v1.sqlite3" ] && { mv -f "$DATA_DIR/franchise_analytics_v1.sqlite3" "$CUR_BAK_DIR/franchise_analytics_v1.sqlite3" || rollback_swap; }
     [ -f "$DATA_DIR/ftc_macro_statistics_v1.sqlite3" ] && { mv -f "$DATA_DIR/ftc_macro_statistics_v1.sqlite3" "$CUR_BAK_DIR/ftc_macro_statistics_v1.sqlite3" || rollback_swap; }

     # 교체용 .new 파일을 정식 운영 DB로 원자적 이동 (실패 시 즉시 중단 및 원상복구)
     mv -f "$DATA_DIR/brand_master_v1.sqlite3.new" "$DATA_DIR/brand_master_v1.sqlite3" || rollback_swap
     mv -f "$DATA_DIR/franchise_analytics_v1.sqlite3.new" "$DATA_DIR/franchise_analytics_v1.sqlite3" || rollback_swap
     mv -f "$DATA_DIR/ftc_macro_statistics_v1.sqlite3.new" "$DATA_DIR/ftc_macro_statistics_v1.sqlite3" || rollback_swap

     # 3개 DB 교체가 모두 검증 완료된 후에만 임시 백업 및 스테이징 디렉터리 정리
     rm -rf "$CUR_BAK_DIR"
     rm -rf "$STAGING_DIR"
     chown franchise:franchise "$DATA_DIR"/*.sqlite3
     chmod 644 "$DATA_DIR"/*.sqlite3
     echo "[SUCCESS] 3개 서비스 DB 원자적 교체 및 권한 설정 완료"
     '
     ```
  3. **서비스 재기동 및 최종 헬스체크**:
     ```bash
     sudo systemctl start franchise-dashboard
     curl -f http://127.0.0.1:8000/api/health
     ```

---

## 7. 배포 결정 매트릭스 (Go / No-Go Decision Matrix)

| 구분 | 검사항목 | 판단 기준 | 미충족 시 조치 |
|---|---|---|---|
| **사전 요건** | 사용자 명시 승인 | 사용자가 실제 배포 실행을 명시 승인했는가? | **배포 즉시 중단 (대기)** |
| **사전 요건** | 필수 입력값 11종 | IP, 도메인, SSH 키, 이메일 등 11종 입력 완료 여부 | 미입력 항목 보완 요청 |
| **인프라** | 서버 사양 충족 | Ubuntu 24.04, 최소 2 vCPU / 4GB RAM / 30GB SSD 이상 | 인스턴스 스펙 업그레이드 |
| **네트워크** | 도메인 DNS A 레코드 | `OPERATING_DOMAIN`이 `SERVER_PUBLIC_IP`를 가리키는가? | DNS 레코드 전파 완료 대기 |
| **보안** | 방화벽 UFW | 80, 443 오픈 및 22번 포트 관리자 IP 한정 설정 완료 | UFW 규칙 재설정 |
| **무결성** | 서비스 DB 3종 | 3개 DB 모두 `PRAGMA integrity_check = ok`인가? | 원본 로컬 DB 재동기화 |
| **품질** | 직후 검증 6종 | V-01 ~ V-06 검증 테스트 100% 통과 여부 | Level 1~3 롤백 가동 |
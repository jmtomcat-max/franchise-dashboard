#!/usr/bin/env bash
# ==============================================================================
# Franchise Dashboard - Single Server Provisioning & Setup Guide Script
# 대상 OS: Ubuntu 22.04 / 24.04 LTS
# 주의: 이 스크립트는 실제 원격 실행용이 아닌 서버 설정 가이드/참조 템플릿입니다.
# ==============================================================================

set -euo pipefail

APP_DIR="/opt/franchise-dashboard"
LOG_DIR="/var/log/franchise-dashboard"
BACKUP_DIR="${APP_DIR}/backups"
APP_USER="franchise"
APP_GROUP="franchise"

echo "[1/6] 전용 서비스 계정 및 디렉터리 구조 확인..."
if ! id "${APP_USER}" &>/dev/null; then
    sudo useradd -r -s /usr/sbin/nologin -d "${APP_DIR}" "${APP_USER}" || true
fi

# Nginx(www-data) 및 Caddy(caddy) 웹서버 계정에 frontend/dist 읽기 권한 부여
for WEB_USER in www-data caddy; do
    if id "${WEB_USER}" &>/dev/null; then
        sudo usermod -a -G "${APP_GROUP}" "${WEB_USER}" || true
    fi
done

sudo mkdir -p "${APP_DIR}" "${LOG_DIR}" "${BACKUP_DIR}" "${APP_DIR}/data" "${APP_DIR}/frontend/dist"
sudo chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}" "${LOG_DIR}"

# 상위 디렉터리 탐색 허용 (755) 및 정적 배포 디렉터리 웹서버 읽기 권한 보장
sudo chmod 755 "${APP_DIR}"
sudo chmod -R 755 "${APP_DIR}/frontend"
sudo chmod 755 "${LOG_DIR}"
sudo chmod 700 "${BACKUP_DIR}"

# 환경변수 파일 보안 격리 (franchise 계정 전용 읽기)
if [ -f "${APP_DIR}/.env.production" ]; then
    sudo chmod 600 "${APP_DIR}/.env.production"
fi

echo "[2/6] SQLite 운영 DB 읽기 전용 권한 설정..."
# DB 디렉터리는 읽기 전용으로 보호 (배포 계정만 업데이트 가능)
if [ -f "${APP_DIR}/data/brand_master_v1.sqlite3" ]; then
    sudo chmod 644 "${APP_DIR}/data/brand_master_v1.sqlite3"
fi

echo "[3/6] Python 가상환경 및 의존성 설치 가이드..."
# python3.12 -m venv ${APP_DIR}/.venv
# ${APP_DIR}/.venv/bin/pip install --upgrade pip
# ${APP_DIR}/.venv/bin/pip install -r ${APP_DIR}/requirements.txt

echo "[4/6] systemd 서비스 등록..."
# sudo cp ${APP_DIR}/deploy/franchise-dashboard.service /etc/systemd/system/
# sudo systemctl daemon-reload
# sudo systemctl enable franchise-dashboard
# sudo systemctl restart franchise-dashboard

echo "[5/6] Reverse Proxy (Nginx) 설정 및 TLS 인증서 발급 가이드..."
# [5-1단계: 초기 HTTP 부트스트랩 활성화 (인증서 발급 전)]
# 신규 서버에서는 /etc/letsencrypt 인증서가 없으므로 처음부터 HTTPS 설정을 켜면 nginx -t가 실패합니다.
# 1) Let's Encrypt ACME 챌린지 디렉터리 생성:
#    sudo mkdir -p /var/www/certbot
# 2) HTTP 전용 부트스트랩 템플릿 배포 및 Nginx 기동:
#    sudo cp ${APP_DIR}/deploy/nginx-bootstrap.conf /etc/nginx/sites-available/franchise-dashboard-bootstrap.conf
#    sudo sed -i 's/dashboard.example.com/실제운영도메인/g' /etc/nginx/sites-available/franchise-dashboard-bootstrap.conf
#    sudo ln -sf /etc/nginx/sites-available/franchise-dashboard-bootstrap.conf /etc/nginx/sites-enabled/
#    sudo rm -f /etc/nginx/sites-enabled/default
#    sudo nginx -t && sudo systemctl reload nginx
# 3) Certbot Webroot 플러그인을 통한 무료 TLS 인증서 발급 및 자동 갱신 리로드 훅 등록:
#    sudo apt install -y certbot python3-certbot-nginx
#    sudo certbot certonly --webroot -w /var/www/certbot -d 실제운영도메인 --non-interactive --agree-tos -m admin@실제운영도메인 --deploy-hook "systemctl reload nginx"
#    # (선택) 글로벌 갱신 훅 스크립트 등록 (certbot.timer 갱신 성공 시 Nginx 자동 리로드 보장):
#    # sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh > /dev/null << 'EOF'
#    # #!/bin/sh
#    # nginx -t && systemctl reload nginx
#    # EOF
#    # sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
#    # 갱신 드라이런 테스트:
#    # sudo certbot renew --dry-run
#
# [5-2단계: HTTPS 메인 Nginx 설정 활성화 및 전환]
# 인증서 발급 확인 후 (/etc/letsencrypt/live/실제운영도메인/fullchain.pem):
#    sudo cp ${APP_DIR}/deploy/nginx.conf /etc/nginx/sites-available/franchise-dashboard.conf
#    sudo sed -i 's/dashboard.example.com/실제운영도메인/g' /etc/nginx/sites-available/franchise-dashboard.conf
#    sudo ln -sf /etc/nginx/sites-available/franchise-dashboard.conf /etc/nginx/sites-enabled/
#    sudo rm -f /etc/nginx/sites-enabled/franchise-dashboard-bootstrap.conf
#    sudo nginx -t && sudo systemctl reload nginx
#
# [대안: Caddy 사용 시 (자동 TLS)]
# Caddy(deploy/Caddyfile)는 내장 ACME 클라이언트를 통해 도메인 지정 시 Let's Encrypt 인증서를
# 전자동 발급/적용하므로 위 2단계 부트스트랩 없이 즉시 HTTPS 가동 가능:
#    sudo cp ${APP_DIR}/deploy/Caddyfile /etc/caddy/Caddyfile
#    sudo sed -i 's/dashboard.example.com/실제운영도메인/g' /etc/caddy/Caddyfile
#    sudo systemctl reload caddy

echo "[6/6] 일일 자동 백업 cron 등록 가이드 (매일 새벽 03:00)..."
# echo "0 3 * * * ${APP_USER} ${APP_DIR}/.venv/bin/python ${APP_DIR}/scripts/backup_production_db.py --target-dir ${BACKUP_DIR} >> ${LOG_DIR}/backup.log 2>&1" | sudo tee /etc/cron.d/franchise-backup

echo "서버 설정 템플릿 검토 완료. 실제 실행 시에는 도메인 및 환경변수(.env.production)를 먼저 입력하십시오."

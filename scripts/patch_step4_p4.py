import re
from pathlib import Path

def patch_runbook_p4():
    runbook_path = Path("reports/phase7_step4_predeployment_runbook.md")
    content = runbook_path.read_text(encoding="utf-8").replace("\r\n", "\n")

    # 1. Fix bad substitution
    target1 = """         # BACKUP_DESTINATION이 /opt/franchise-dashboard 하위에 위치할 경우 해당 경로를 동적으로 제외하여 백업 삭제 방지
         BACKUP_EXCLUDE_ARG=""
         case "<BACKUP_DESTINATION>" in
             /opt/franchise-dashboard/*)
                 REL_BACKUP_PATH="${<BACKUP_DESTINATION>#/opt/franchise-dashboard/}"
                 BACKUP_EXCLUDE_ARG="--exclude=${REL_BACKUP_PATH}*"
                 ;;
         esac"""

    repl1 = """         # BACKUP_DESTINATION이 /opt/franchise-dashboard 하위에 위치할 경우 해당 경로를 동적으로 제외하여 백업 삭제 방지
         RAW_BACKUP_DEST="<BACKUP_DESTINATION>"
         BACKUP_EXCLUDE_ARG=""
         case "$RAW_BACKUP_DEST" in
             /opt/franchise-dashboard/*)
                 REL_BACKUP_PATH="${RAW_BACKUP_DEST#/opt/franchise-dashboard/}"
                 BACKUP_EXCLUDE_ARG="--exclude=${REL_BACKUP_PATH}*"
                 ;;
         esac"""

    # 2. Preserve static assets in Level 1 rollback
    target2 = """            if [ -n "$PREV_REL" ] && [ -f "${PREV_REL}/index.html" ]; then
                echo "[INFO] 배포 시작 시점의 라이브 릴리스(${PREV_REL})로 정적 서빙 심볼릭 링크를 원자적으로 즉시 복원합니다."
                sudo -u franchise ln -sfn "${PREV_REL}" /opt/franchise-dashboard/frontend/dist.tmp || {"""

    repl2 = """            if [ -n "$PREV_REL" ] && [ -f "${PREV_REL}/index.html" ]; then
                # 롤백 직전에 새 버전 HTML을 내려받은 사용자가 롤백 후 후속 chunk(JS/CSS) 요청 시 404가 발생하지 않도록,
                # 현재 서비스 중인 릴리스의 해시 정적 에셋(dist/assets/*)을 복원 대상 릴리스(${PREV_REL}/assets/)에 비파괴 병합
                if [ -d "/opt/franchise-dashboard/frontend/dist/assets" ] && [ -d "${PREV_REL}/assets" ]; then
                    echo "[INFO] 롤백 전 페이지 사용자의 404를 방지하기 위해 현재 릴리스 에셋을 복원 대상에 비파괴 병합(cp -n)합니다."
                    sudo -u franchise cp -n /opt/franchise-dashboard/frontend/dist/assets/* "${PREV_REL}/assets/" 2>/dev/null || true
                fi

                echo "[INFO] 배포 시작 시점의 라이브 릴리스(${PREV_REL})로 정적 서빙 심볼릭 링크를 원자적으로 즉시 복원합니다."
                sudo -u franchise ln -sfn "${PREV_REL}" /opt/franchise-dashboard/frontend/dist.tmp || {"""

    assert target1 in content, "target1 not found"
    assert target2 in content, "target2 not found"

    content = content.replace(target1, repl1, 1)
    content = content.replace(target2, repl2, 1)

    runbook_path.write_text(content, encoding="utf-8")
    print("[PASS] Runbook P4 feedback cleanly applied!")

if __name__ == "__main__":
    patch_runbook_p4()

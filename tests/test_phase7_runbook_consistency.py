#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 7 Step 7-4 Runbook & Checklist 정합성 회귀 테스트
실제 파일 정합성 통과 검증 및 불일치(변조/누락) 시 반드시 실패하는지 실증합니다.
"""

import copy
import json
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify_step4_runbook_consistency import (
    RUNBOOK_MD_PATH,
    CHECKLIST_JSON_PATH,
    verify_runbook_consistency,
)

class TestRunbookConsistency(unittest.TestCase):
    def setUp(self):
        self.md_text = RUNBOOK_MD_PATH.read_text(encoding="utf-8")
        self.json_data = json.loads(CHECKLIST_JSON_PATH.read_text(encoding="utf-8"))

    def _verify(self, md_text, json_data, check_bash_syntax=False):
        return verify_runbook_consistency(md_text, json_data, check_bash_syntax=check_bash_syntax)

    def test_actual_files_pass_consistency(self):
        """실제 산출물 파일 간의 정합성이 100% PASS하는지 검증합니다 (bash -n 포함)."""
        success, errors = self._verify(self.md_text, self.json_data, check_bash_syntax=True)
        self.assertTrue(success, f"실제 파일 검증 실패: {errors}")
        self.assertEqual(len(errors), 0)

    def test_detects_mismatched_hardware_specs(self):
        """Markdown 내 사양 수치가 변조되면(예: 99/99/99) 즉시 실패를 검출하는지 검증합니다."""
        tampered_md = self.md_text.replace(
            "4 vCPU / 8 GB RAM / 50 GB NVMe SSD",
            "99 vCPU / 99 GB RAM / 99 GB NVMe SSD"
        )
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("권장 사양 수치 불일치" in e for e in errors))

    def test_detects_mutated_json_verification_command(self):
        """JSON의 검증 시나리오 명령어가 잘못된 URL로 변조되면 즉시 실패를 검출하는지 검증합니다."""
        bad_json = copy.deepcopy(self.json_data)
        bad_json["verification_scenarios"][0]["command"] = "curl https://wrong.invalid/"
        success, errors = self._verify(self.md_text, bad_json)
        self.assertFalse(success)
        self.assertTrue(any("명령어 불일치" in e for e in errors))

    def test_detects_mutated_json_expected_result(self):
        """JSON의 검증 시나리오 기대 결과가 HTTP 500으로 변조되면 즉시 실패를 검출하는지 검증합니다."""
        bad_json = copy.deepcopy(self.json_data)
        bad_json["verification_scenarios"][0]["expected_result"] = "HTTP 500"
        success, errors = self._verify(self.md_text, bad_json)
        self.assertFalse(success)
        self.assertTrue(any("기대결과 불일치" in e for e in errors))

    def test_detects_mutated_json_ports(self):
        """JSON의 공개 포트가 8000 등으로 변조되면 즉시 실패를 검출하는지 검증합니다."""
        bad_json = copy.deepcopy(self.json_data)
        bad_json["server_specification"]["ports"]["inbound_public"] = [8000]
        success, errors = self._verify(self.md_text, bad_json)
        self.assertFalse(success)
        self.assertTrue(any("inbound_public 포트 불일치" in e for e in errors))

    def test_detects_missing_mandatory_packages(self):
        """Markdown에서 필수 패키지 설치 명령이 제거되거나 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace(
            "sudo apt install -y python3 python3-pip python3-venv git curl ufw nginx certbot python3-certbot-nginx sqlite3 logrotate rsync",
            "sudo apt install -y python3"
        )
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("필수 패키지 설치 명령에서" in e for e in errors))

    def test_detects_missing_certbot_deploy_hook(self):
        """Certbot 명령어에서 --deploy-hook 'systemctl reload nginx'가 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace(
            '--deploy-hook "systemctl reload nginx"',
            '--manual'
        )
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("deploy-hook" in e for e in errors))

    def test_detects_mismatched_input_keys(self):
        """입력값 11종 중 하나가 표에서 누락되거나 변조되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("SERVER_PROVIDER", "INVALID_PROVIDER")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("입력값 키 목록 불일치" in e for e in errors))

    def test_detects_v05_wildcard_regression(self):
        """V-05에서 실제 JS 자산 파일명 추출 로직이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("ASSET_JS=$(", "NO_ASSET_JS=(")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("V-05" in e for e in errors))

    def test_detects_missing_staging_dir_or_checksum_in_level3(self):
        """Level 3 복구 절차에서 동일 파일시스템 스테이징이나 sha256sum이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace(".restore_staging", "wrong_dir")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("동일 파일시스템 내 스테이징" in e for e in errors))

    def test_detects_duplicated_verification_scenarios(self):
        """검증 시나리오 V-01이 복제되어 ID 목록이 일치하지 않을 때 실패하는지 검증합니다."""
        tampered_json = copy.deepcopy(self.json_data)
        tampered_json["verification_scenarios"] = [copy.deepcopy(tampered_json["verification_scenarios"][0]) for _ in range(6)]
        success, errors = self._verify(self.md_text, tampered_json)
        self.assertFalse(success)
        self.assertTrue(any("verification_scenarios ID 목록 오류" in e for e in errors))

    def test_detects_missing_cd_backup_destination_in_level3(self):
        """Level 3 복구 절차에서 백업 디렉터리 이동(cd <BACKUP_DESTINATION>)이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("cd <BACKUP_DESTINATION>", "cd /wrong/path")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("백업 디렉터리 이동" in e for e in errors))

    def test_detects_missing_sudo_bash_in_level3(self):
        """Level 3 복구 절차에서 권한 있는 동일 셸(sudo bash -c) 실행이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("sudo bash -c", "# bash -c")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("권한 있는 동일 셸" in e for e in errors))

    def test_detects_missing_rollback_swap_in_level3(self):
        """Level 3 복구 절차에서 DB 교체 실패 시 롤백 함수(rollback_swap)가 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("rollback_swap", "no_rollback")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("rollback_swap" in e for e in errors))

    def test_detects_removed_rollback_swap_call_sites(self):
        """Markdown Level 3에서 || rollback_swap 호출부가 제거되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace(" || rollback_swap", "")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("실패 처리 연결(|| rollback_swap) 호출부" in e for e in errors))

    def test_detects_tampered_json_level3_action(self):
        """Checklist JSON Level 3의 action이 무관한 내용('NO RESTORE')으로 변조되면 실패하는지 검증합니다."""
        tampered_json = copy.deepcopy(self.json_data)
        tampered_json["rollback_plan"][2]["action"] = "NO RESTORE"
        success, errors = self._verify(self.md_text, tampered_json)
        self.assertFalse(success)
        self.assertTrue(any("Checklist JSON Level 3 action에 필수 키워드" in e for e in errors))

    def test_detects_missing_cur_bak_dir_in_level3(self):
        """Markdown Level 3에서 CUR_BAK_DIR 고유 백업 디렉터리 격리가 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("CUR_BAK_DIR=", "NO_BAK_DIR=")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("CUR_BAK_DIR" in e for e in errors))

    def test_detects_missing_new_swap_file_in_level3(self):
        """Markdown Level 3에서 스테이징 원본 보존용 .new 교체 임시 파일이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace(".sqlite3.new", ".sqlite3")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any(".new" in e for e in errors))

    def test_detects_missing_env_exclusion_in_rsync(self):
        """rsync 전송 명령에서 --exclude='.env*'가 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("--exclude='.env*'", "--exclude='.dummy'")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("비밀정보 제외(--exclude='.env*')" in e for e in errors))

    def test_detects_unfiltered_cp_overwriting_data(self):
        """data 디렉터리를 덮어쓰는 위험한 cp -r 명령어가 포함되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace(
            "sudo rsync -av --exclude='data' --exclude='backups' --exclude='.env*' --exclude='frontend/dist*' /tmp/franchise-dashboard-source/ /opt/franchise-dashboard/",
            "sudo cp -r /tmp/franchise-dashboard-source/* /opt/franchise-dashboard/"
        )
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("data/ 디렉터리를 무단 덮어쓰는 위험한 cp -r" in e for e in errors))

    def test_detects_empty_phase_key_actions(self):
        """Checklist JSON Phase의 key_actions가 빈 배열로 변조되면 실패하는지 검증합니다."""
        tampered_json = copy.deepcopy(self.json_data)
        tampered_json["execution_phases"][2]["key_actions"] = []
        success, errors = self._verify(self.md_text, tampered_json)
        self.assertFalse(success)
        self.assertTrue(any("key_actions 항목이 부족하거나 비어있습니다" in e for e in errors))

    def test_detects_missing_tmp_franchise_data_staging(self):
        """Markdown Phase 3에서 전용 DB 전송 스테이징 경로가 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("/tmp/franchise-dashboard-data/", "/tmp/wrong-path/")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("전용 DB 전송 및 배치(/tmp/franchise-dashboard-data/)" in e for e in errors))

    def test_detects_duplicate_phase_numbers_all_phase1(self):
        """Checklist JSON의 execution_phases가 Phase 1 복사본 8개로 변조되면 실패하는지 검증합니다."""
        tampered_json = copy.deepcopy(self.json_data)
        phase1_copy = copy.deepcopy(tampered_json["execution_phases"][0])
        tampered_json["execution_phases"] = [copy.deepcopy(phase1_copy) for _ in range(8)]
        success, errors = self._verify(self.md_text, tampered_json)
        self.assertFalse(success)
        self.assertTrue(any("phase_number 순서 또는 단계 오류" in e for e in errors))

    def test_detects_non_sequential_phase_numbers(self):
        """Checklist JSON의 execution_phases 번호 순서가 어긋나거나 중복/누락되면 실패하는지 검증합니다."""
        tampered_json = copy.deepcopy(self.json_data)
        tampered_json["execution_phases"][3]["phase_number"] = 3 # 4번을 3번으로 중복
        success, errors = self._verify(self.md_text, tampered_json)
        self.assertFalse(success)
        self.assertTrue(any("phase_number 순서 또는 단계 오류" in e for e in errors))

    def test_detects_missing_phase3_db_rsync_command(self):
        """Markdown Phase 3에서 DB 전용 rsync 업로드 명령 블록 전체가 삭제되면 실패하는지 검증합니다."""
        target_block = (
            '     rsync -avz -e "ssh -i <SSH_PRIVATE_KEY_PATH> -p <SSH_PORT>" \\\n'
            '         ./data/brand_master_v1.sqlite3 \\\n'
            '         ./data/franchise_analytics_v1.sqlite3 \\\n'
            '         ./data/ftc_macro_statistics_v1.sqlite3 \\\n'
            '         <SSH_USER>@<SERVER_PUBLIC_IP>:/tmp/franchise-dashboard-data/'
        )
        self.assertIn(target_block, self.md_text, "Markdown 원본에 해당 rsync 명령 블록이 존재해야 합니다.")
        tampered_md = self.md_text.replace(target_block, "# [DELETED] DB rsync command removed")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("DB 3종 전용 rsync 전송 명령(목적지 /tmp/franchise-dashboard-data/)이 누락되었거나 변조되었습니다" in e for e in errors))

    def test_detects_missing_database_in_rsync(self):
        """Markdown Phase 3 DB 전용 rsync 업로드 명령에서 특정 DB(brand_master_v1.sqlite3)가 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("./data/brand_master_v1.sqlite3", "./data/wrong_db.sqlite3")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("대상 DB 'brand_master_v1.sqlite3'이(가) 누락되었습니다" in e for e in errors))

    def test_detects_tampered_db_rsync_destination(self):
        """Markdown Phase 3 DB rsync 업로드 명령의 대상 경로가 /tmp/franchise-dashboard-data/가 아니면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace(
            "<SSH_USER>@<SERVER_PUBLIC_IP>:/tmp/franchise-dashboard-data/",
            "<SSH_USER>@<SERVER_PUBLIC_IP>:/tmp/wrong-destination/"
        )
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("DB 3종 전용 rsync 전송 명령(목적지 /tmp/franchise-dashboard-data/)이 누락되었거나 변조되었습니다" in e for e in errors))

    def test_detects_tampered_go_no_go_criteria(self):
        """Checklist JSON의 Go/No-Go decision matrix에서 criteria가 변조되면 실패하는지 검증합니다."""
        tampered_json = copy.deepcopy(self.json_data)
        tampered_json["go_no_go_decision_matrix"][2]["criteria"] = "Ubuntu 22.04, minimum 1 vCPU / 1GB RAM / 5GB SSD"
        success, errors = self._verify(self.md_text, tampered_json)
        self.assertFalse(success)
        self.assertTrue(any("판단 기준 불일치" in e for e in errors))

    def test_detects_tampered_go_no_go_action_on_failure(self):
        """Checklist JSON의 Go/No-Go decision matrix에서 action_on_failure가 변조되면 실패하는지 검증합니다."""
        tampered_json = copy.deepcopy(self.json_data)
        tampered_json["go_no_go_decision_matrix"][0]["action_on_failure"] = "무시하고 배포 계속 진행"
        success, errors = self._verify(self.md_text, tampered_json)
        self.assertFalse(success)
        self.assertTrue(any("미충족 시 조치 불일치" in e for e in errors))

    def test_detects_missing_00_franchise_security_conf(self):
        """Markdown Phase 1에서 최우선 순위 SSH 설정 파일(00-franchise-security.conf)이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("00-franchise-security.conf", "99-wrong-security.conf")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("최우선 순위 SSH 설정(00-franchise-security.conf)" in e for e in errors))

    def test_detects_duplicate_go_no_go_items_all_first_item(self):
        """Checklist JSON의 Go/No-Go 목록을 첫 항목의 복사본 7개로 교체했을 때 실패하는지 검증합니다."""
        tampered_json = copy.deepcopy(self.json_data)
        tampered_json["go_no_go_decision_matrix"] = [
            copy.deepcopy(tampered_json["go_no_go_decision_matrix"][0]) for _ in range(7)
        ]
        success, errors = self._verify(self.md_text, tampered_json)
        self.assertFalse(success)
        self.assertTrue(any("중복된 검사항목이 존재합니다" in e for e in errors))

    def test_detects_removed_real_sshd_t_execution_command_with_comments_retained(self):
        """Markdown Phase 1에서 설명·주석은 유지한 채 실제 sudo sshd -T 실행 줄만 제거했을 때 실패하는지 검증합니다."""
        cmd_line = next(x for x in self.md_text.splitlines() if x.strip().startswith("sudo sshd -T"))
        tampered_md = self.md_text.replace(cmd_line, "   # [REMOVED] command removed but comments remain")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("실제 'sudo sshd -T | grep ...' 실행 명령 줄이 누락되었거나 변조되었습니다" in e for e in errors))

    def test_detects_missing_ufw_prerequisite_install(self):
        """Markdown Phase 1에서 UFW 사전 설치 확인 및 미설치 시 설치 절차가 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("which ufw", "echo no-ufw-check")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("UFW 사전 설치 확인(which ufw)" in e for e in errors))

    def test_detects_missing_prev_source_snapshot_backup_and_restore(self):
        """Markdown Phase 3 및 Level 1에서 직전 소스 스냅샷(/opt/franchise-dashboard-prev-source) 절차가 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("/opt/franchise-dashboard-prev-source", "/opt/wrong-snapshot-path")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("기존 배포 소스 스냅샷 백업(/opt/franchise-dashboard-prev-source)" in e for e in errors))

    def test_detects_missing_phase3_tmp_source_snapshot_or_swap(self):
        """Markdown Phase 3에서 임시 스냅샷 경로(/opt/.franchise-dashboard-prev-source.tmp) 또는 원자적 교체가 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("/opt/.franchise-dashboard-prev-source.tmp", "/opt/direct-overwrite")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("소스 스냅샷 안전 임시 생성 경로" in e for e in errors))

    def test_detects_missing_level1_npm_ci_or_abort(self):
        """Markdown Level 1 롤백에서 npm ci 또는 실패 시 서비스 기동 차단(exit 1)이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("npm --prefix frontend ci", "echo skipping-ci")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("이전 package-lock.json 기준 의존성 복원(npm --prefix frontend ci)" in e for e in errors))

    def test_detects_missing_phase6_backend_restart_command(self):
        """Markdown Phase 6에서 신규 배포 및 재배포 시 프로세스 전환을 보장하는 systemctl restart 명령이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("sudo systemctl restart franchise-dashboard", "sudo systemctl start franchise-dashboard")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("sudo systemctl restart franchise-dashboard" in e for e in errors))

    def test_detects_missing_phase3_dist_exclude(self):
        """Markdown Phase 3에서 운영 정적 서빙 파일 덮어쓰기 방지를 위한 frontend/dist* 제외 옵션이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("--exclude='frontend/dist*'", "--exclude='frontend/legacy*'")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("frontend/dist* 제외 옵션" in e for e in errors))

    def test_detects_missing_phase3_source_rsync_failure_abort(self):
        """Markdown Phase 3에서 소스코드 반영 rsync 실패 시 즉시 중단(exit 1) 방어 로직이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace(
            "sudo rsync -av --exclude='data' --exclude='backups' --exclude='.env*' --exclude='frontend/dist*' /tmp/franchise-dashboard-source/ /opt/franchise-dashboard/ || {",
            "sudo rsync -av --exclude='data' --exclude='backups' --exclude='.env*' --exclude='frontend/dist*' /tmp/franchise-dashboard-source/ /opt/franchise-dashboard/"
        )
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("소스코드 반영 rsync 실패 시 배포를 즉시 중단" in e for e in errors))

    def test_detects_missing_phase5_atomic_symlink_swap(self):
        """Markdown Phase 5에서 다운타임 0초 전환을 위한 releases/ 독립 빌드 또는 mv -Tf 원자적 심볼릭 링크 스왑이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("mv -Tf", "mv -f")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("무중단 원자적 심볼릭 링크 스왑" in e for e in errors))

    def test_detects_missing_level1_rsync_delete_and_dist_exclude(self):
        """Markdown Level 1 롤백에서 소스 복원 시 --delete 또는 frontend/dist* 제외가 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("sudo rsync -av --delete", "sudo rsync -av")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("소스 스냅샷 복원 rsync 실행 명령(--delete 및 frontend/dist* 제외)" in e for e in errors))

    def test_detects_missing_level1_atomic_symlink_rollback(self):
        """Markdown Level 1 롤백에서 정적 서빙 직전 릴리스 원자적 심볼릭 링크 롤백(sudo -u franchise ln -sfn & mv -Tf)이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("sudo -u franchise ln -sfn \"${PREV_REL}\"", "# skipping symlink rollback")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("정적 서빙 직전 릴리스 원자적 심볼릭 링크 롤백" in e for e in errors))

    def test_detects_missing_previous_live_release_tracking(self):
        """Markdown Phase 5 또는 Level 1에서 previous_live_release.txt 추적/복원이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("previous_live_release.txt", "wrong_release_file.txt")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("previous_live_release.txt" in e for e in errors))

    def test_detects_missing_level1_checklist_json_symlink_rollback_keyword(self):
        """Checklist JSON Level 1 action에서 '원자적 심볼릭 링크 롤백' 키워드가 누락되면 실패하는지 검증합니다."""
        tampered_json = copy.deepcopy(self.json_data)
        for r in tampered_json["rollback_plan"]:
            if r["level"] == 1:
                r["action"] = "systemctl restart franchise-dashboard 및 journalctl 로그 분석 후 재기동"
        success, errors = self._verify(self.md_text, tampered_json)
        self.assertFalse(success)

    def test_detects_missing_legacy_dist_rollback_on_swap_failure(self):
        """Markdown Phase 5에서 일반 디렉터리 최초 전환 시 실패 원상복구 방어벽(LEGACY_DIST_DIR)이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("LEGACY_DIST_DIR", "WRONG_DIST_DIR")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("일반 디렉터리 최초 전환 시 실패 원상복구 방어벽" in e for e in errors))

    def test_detects_wrong_ftc_macro_table_name(self):
        """Markdown Phase 3에서 실제 존재하는 FTC 테이블명(ftc_industry_macro_summary)이 아니거나 macro_indicators가 포함되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("ftc_industry_macro_summary", "macro_indicators")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("ftc_industry_macro_summary" in e or "macro_indicators" in e for e in errors))

    def test_detects_missing_deploy_start_live_release_tracking(self):
        """Markdown Phase 3에서 배포 시작 시점의 라이브 릴리스 기록(deploy_start_live_release.txt)이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace("deploy_start_live_release.txt", "wrong_live_release_file.txt")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("deploy_start_live_release.txt" in e for e in errors))

    def test_detects_unhandled_asset_copy_failure(self):
        """Markdown Phase 5에서 이전 릴리스 정적 에셋 병합 실패 시 즉시 중단(exit 1) 방어벽이 누락되면 실패하는지 검증합니다."""
        import re
        tampered_md = re.sub(
            r'sudo -u franchise cp -n [^\n]+assets/\*[\s\S]+?exit 1\s*\}',
            'sudo -u franchise cp -n /opt/franchise-dashboard/frontend/dist/assets/* "${RELEASE_DIR}/assets/" 2>/dev/null || true',
            self.md_text
        )
        self.assertNotEqual(tampered_md, self.md_text, "치환 대상 블록이 발견되어야 합니다.")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("이전 릴리스 정적 에셋 병합 실패 시 즉시 중단" in e for e in errors))

    def test_detects_bash_syntax_error_in_code_block(self):
        """Markdown 내 bash 코드 블록에 중복 fi 등 문법 오류가 주입되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace(
            'echo "[INFO] 기존 릴리스 소스 스냅샷 안전 보존 완료: $PREV_SRC_BACKUP"',
            'echo "[INFO] 기존 릴리스 소스 스냅샷 안전 보존 완료: $PREV_SRC_BACKUP"\n    fi\n    fi'
        )
        success, errors = self._verify(tampered_md, self.json_data, check_bash_syntax=True)
        self.assertFalse(success)
        self.assertTrue(any("bash -n 구문 오류" in e for e in errors))

    def test_detects_missing_level1_asset_copy_failure_abort(self):
        """Markdown Level 1 롤백에서 정적 에셋 보존 cp -n 실패 시 즉시 중단(exit 1) 방어벽이 누락되면 실패하는지 검증합니다."""
        tampered_md = self.md_text.replace(
            'sudo -u franchise cp -n /opt/franchise-dashboard/frontend/dist/assets/* "${PREV_REL}/assets/" || {',
            'sudo -u franchise cp -n /opt/franchise-dashboard/frontend/dist/assets/* "${PREV_REL}/assets/" 2>/dev/null || true'
        )
        self.assertNotEqual(tampered_md, self.md_text, "치환 대상 블록이 발견되어야 합니다.")
        success, errors = self._verify(tampered_md, self.json_data)
        self.assertFalse(success)
        self.assertTrue(any("정적 에셋 보존(cp -n) 실패 시 즉시 중단" in e for e in errors))

if __name__ == "__main__":
    unittest.main()







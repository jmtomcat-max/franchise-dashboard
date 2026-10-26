"""
Phase 7 Step 7-3 회귀 테스트: SQLite 백업 보존 일수(retention-days) 안전성 검증
위치: tests/test_phase7_backup_retention.py

검증 대상:
1. retention_days가 0 또는 음수일 때 ValueError 발생 및 방금 생성된 백업 파일 삭제 방지
2. 정상적인 retention_days에서 과거 백업만 회전되고 신규 백업은 온전히 보존
3. CLI 실행 시 백업 시작 전 retention-days < 1 검증 차단
"""

import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.backup_production_db import rotate_old_backups, main as backup_main


class TestBackupRetentionSafety(unittest.TestCase):
    def test_rotate_old_backups_rejects_zero_and_negative(self):
        """retention_days가 0 또는 음수일 때 즉시 ValueError를 발생시키고 삭제를 수행하지 않아야 합니다."""
        mock_dir = Mock(spec=Path)
        mock_item = Mock()
        mock_item.name = "brand_master_v1_backup_new.sqlite3"
        mock_item.stat.return_value.st_mtime = time.time() - 1
        mock_dir.glob.return_value = [mock_item]

        # 1. retention_days = 0 시 ValueError 발생 및 unlink 미호출 확인
        with self.assertRaises(ValueError) as ctx_zero:
            rotate_old_backups(mock_dir, retention_days=0)
        self.assertIn("최소 1일 이상", str(ctx_zero.exception))
        mock_item.unlink.assert_not_called()

        # 2. retention_days = -1 시 ValueError 발생 및 unlink 미호출 확인
        with self.assertRaises(ValueError) as ctx_neg:
            rotate_old_backups(mock_dir, retention_days=-1)
        self.assertIn("최소 1일 이상", str(ctx_neg.exception))
        mock_item.unlink.assert_not_called()

    def test_rotate_old_backups_preserves_new_backup_and_removes_old(self):
        """retention_days=7일 때 1일 전 신규 파일은 보존되고 10일 전 구형 파일만 삭제되어야 합니다."""
        mock_dir = Mock(spec=Path)
        now = datetime.now()

        # 1일 전 파일 (보존 대상)
        recent_item = Mock()
        recent_item.name = "brand_master_v1_backup_recent.sqlite3"
        recent_item.stat.return_value.st_mtime = (now - timedelta(days=1)).timestamp()

        # 10일 전 파일 (삭제 대상)
        old_item = Mock()
        old_item.name = "brand_master_v1_backup_old.sqlite3"
        old_item.stat.return_value.st_mtime = (now - timedelta(days=10)).timestamp()

        mock_dir.glob.return_value = [recent_item, old_item]

        removed_count = rotate_old_backups(mock_dir, retention_days=7)

        self.assertEqual(removed_count, 1)
        recent_item.unlink.assert_not_called()
        old_item.unlink.assert_called_once()

    def test_main_rejects_invalid_retention_days_before_backup(self):
        """CLI 인수로 --retention-days 0 전달 시 백업 복제를 시작하지 않고 즉시 차단되어야 합니다."""
        test_args = ["backup_production_db.py", "--retention-days", "0"]
        with patch.object(sys, "argv", test_args):
            with patch("scripts.backup_production_db.backup_all_service_databases") as mock_backup:
                exit_code = backup_main()
                # 에러 코드로 종료되어야 하고 백업 복제는 한 번도 호출되지 않아야 함
                self.assertEqual(exit_code, 1)
                mock_backup.assert_not_called()


if __name__ == "__main__":
    unittest.main()

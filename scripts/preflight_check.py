#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Franchise Dashboard - 실행환경 사전점검 스크립트 (Preflight Check)
프로젝트: D:/Franchise_Dashboard
위치: scripts/preflight_check.py

새 개발환경 또는 배포 환경에서 시스템이 정상 구동될 수 있는지
Python 런타임, 필수 패키지, SQLite 분석 데이터베이스, 프론트엔드 환경 및
보호 파일 무결성을 종합 점검합니다.
"""

import sys
import os
import sqlite3
import hashlib
import subprocess
from pathlib import Path
from typing import List, Tuple

# Windows 콘솔 UTF-8 출력 보장
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

# 보호 파일 기준 SHA-256 해시값
PROTECTED_FILES = {
    "collector.py": "341BAC12BB0AF58DCBDEBBA9459033521F27DF9817E35BAD8B21A4D07BA3369C",
    "gangnam_food_stores.sqlite3": "FEE3B58651CFED5C390C0B95DB02B05EBE92DF18619A06F4E399D429236F3A78",
    "run_gangnam.bat": "0582C3A1AE53450DDC482E9BF538510780CA2F14D44E987CC753D4E12C816491"
}


class PreflightChecker:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed_count = 0

    def check_python_version(self) -> bool:
        """1. Python 런타임 버전 검사 (Python 3.11 이상 및 .venv 환경 검증)"""
        ver = sys.version_info
        ver_str = f"{ver.major}.{ver.minor}.{ver.micro}"
        is_venv = (sys.prefix != sys.base_prefix) or ("venv" in sys.prefix.lower())
        env_label = "(.venv 활성화)" if is_venv else "(글로벌/시스템 런타임)"
        print(f"[*] Python 런타임 검사: {ver_str} {env_label} ({sys.executable})")
        if ver < (3, 11):
            self.errors.append(f"Python 3.11 이상이 필요합니다. (현재: {ver_str})")
            return False
        self.passed_count += 1
        print("    -> [PASS] Python 3.11+ 요구사항 충족")
        return True

    def check_python_dependencies(self) -> bool:
        """2. 필수 Python 라이브러리 import 가능 여부 검사"""
        print("[*] 필수 Python 패키지 검사...")
        required_modules = ["fastapi", "uvicorn", "pydantic", "httpx", "pytest"]
        all_ok = True
        for mod in required_modules:
            try:
                __import__(mod)
                print(f"    -> [PASS] {mod} 로드 성공")
            except ImportError as e:
                self.errors.append(f"필수 패키지 '{mod}' 누락: {e}")
                all_ok = False
        if all_ok:
            self.passed_count += 1
        return all_ok

    def check_sqlite_databases(self) -> bool:
        """3. 필수 SQLite 분석 DB 파일 및 핵심 테이블/레코드 검사"""
        print("[*] SQLite 분석 데이터베이스 및 스키마 검사...")
        db_checks = [
            (
                BASE_DIR / "data" / "franchise_analytics_v1.sqlite3",
                100 * 1024 * 1024,  # 최소 100MB 이상
                ["store_analytics_lookup", "spatial_density_grid_100m", "commercial_hotspots", "regions_master", "regional_overall_stats", "regional_category_stats", "regional_brand_rankings"]
            ),
            (
                BASE_DIR / "data" / "ftc_macro_statistics_v1.sqlite3",
                1 * 1024 * 1024,    # 최소 1MB 이상
                ["ftc_industry_macro_summary", "ftc_brand_macro_records", "ftc_ingestion_checkpoints"]
            ),
            (
                BASE_DIR / "data" / "brand_master_v1.sqlite3",
                50 * 1024 * 1024,   # 최소 50MB 이상
                ["brands", "brand_aliases", "brand_sources", "brand_franchise_evidence", "store_brand_links"]
            )
        ]
        all_ok = True
        for db_path, min_size, tables in db_checks:
            rel_name = db_path.name
            if not db_path.exists():
                self.errors.append(f"필수 데이터베이스 파일 부재: {db_path}")
                all_ok = False
                continue
            
            size_mb = db_path.stat().st_size / (1024 * 1024)
            if db_path.stat().st_size < min_size:
                self.errors.append(f"{rel_name} 크기가 비정상적으로 작음 ({size_mb:.2f} MB)")
                all_ok = False
                continue
            
            # 읽기 전용 연결 및 테이블 존재 확인 (잠금 경합 및 저널 생성 방지를 위해 mode=ro&immutable=1 적용)
            try:
                db_uri = f"{db_path.resolve().as_uri()}?mode=ro&immutable=1"
                conn = sqlite3.connect(db_uri, uri=True)
                cur = conn.cursor()
                cur.execute("PRAGMA busy_timeout = 5000;")

                # DB 물리적 무결성 검사 (대용량 490MB 분석 DB는 quick_check, 나머지는 integrity_check)
                check_sql = "PRAGMA quick_check;" if rel_name == "franchise_analytics_v1.sqlite3" else "PRAGMA integrity_check;"
                cur.execute(check_sql)
                ic_rows = cur.fetchall()
                if ic_rows != [("ok",)]:
                    self.errors.append(f"{rel_name} 무결성 검사 실패 ({check_sql}): {ic_rows}")
                    all_ok = False
                    conn.close()
                    continue

                cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view');")
                existing_tables = {row[0] for row in cur.fetchall()}

                missing_tables = [t for t in tables if t not in existing_tables]
                if missing_tables:
                    self.errors.append(f"{rel_name} 내 필수 테이블/뷰 누락: {missing_tables}")
                    all_ok = False
                else:
                    extra_info = ""
                    # FTC DB 2023~2026 연도 엄격 검증
                    if rel_name == "ftc_macro_statistics_v1.sqlite3":
                        cur.execute("SELECT DISTINCT jng_biz_crtr_yr FROM ftc_industry_macro_summary ORDER BY jng_biz_crtr_yr")
                        years = [r[0] for r in cur.fetchall()]
                        if years != ["2023", "2024", "2025", "2026"]:
                            self.errors.append(f"FTC 연도 목록 불일치 (기대: ['2023','2024','2025','2026'], 실제: {years})")
                            all_ok = False
                        extra_info = f" (연도: {','.join(years)}, integrity: ok)"
                    elif rel_name == "brand_master_v1.sqlite3":
                        cur.execute("SELECT COUNT(*) FROM brands")
                        brand_cnt = cur.fetchone()[0]
                        cur.execute("SELECT COUNT(*) FROM store_brand_links")
                        link_cnt = cur.fetchone()[0]
                        if brand_cnt < 5063:
                            self.errors.append(f"브랜드 수 기준 미달: {brand_cnt} < 5,063")
                            all_ok = False
                        if link_cnt < 735208:
                            self.errors.append(f"매장-브랜드 링크 수 기준 미달: {link_cnt} < 735,208")
                            all_ok = False
                        extra_info = f" (브랜드: {brand_cnt:,}개, 링크: {link_cnt:,}개, integrity: ok)"
                    else:
                        extra_info = " (integrity: ok)"

                    if all_ok:
                        print(f"    -> [PASS] {rel_name} ({size_mb:.1f} MB) - 무결성/테이블 {len(tables)}개 검증 완료{extra_info}")
                conn.close()
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.errors.append(f"{rel_name} 연결 또는 쿼리 실패: {e}")
                all_ok = False

        if all_ok:
            self.passed_count += 1
        return all_ok

    def check_frontend_environment(self) -> bool:
        """4. 프론트엔드 환경 및 설정 파일 검사"""
        print("[*] 프론트엔드 빌드/실행 환경 검사...")
        frontend_dir = BASE_DIR / "frontend"
        env_file = frontend_dir / ".env"
        all_ok = True

        if not env_file.exists():
            self.errors.append("frontend/.env 파일이 없습니다. (.env.example 복사 필요)")
            all_ok = False
        else:
            # frontend/src/services/api.js에서 실제 사용하는 필수 환경변수 VITE_API_URL 엄격 검증
            with open(env_file, "r", encoding="utf-8") as f:
                env_content = f.read()
            api_url = None
            for line in env_content.splitlines():
                line = line.strip()
                if line.startswith("VITE_API_URL="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        api_url = val
                        break
            if not api_url:
                self.errors.append("frontend/.env 내 필수 환경변수 VITE_API_URL 누락 또는 빈 값 (frontend/src/services/api.js 필수 참조)")
                all_ok = False
            else:
                from urllib.parse import urlparse
                parsed = urlparse(api_url)
                if parsed.scheme not in ("http", "https") or not parsed.netloc:
                    self.errors.append(f"frontend/.env VITE_API_URL 값이 올바른 HTTP/HTTPS URL 형식이 아님: '{api_url}'")
                    all_ok = False
                else:
                    print(f"    -> [PASS] frontend/.env VITE_API_URL 유효성 검증 완료 ({api_url})")

        # Node.js 런타임 확인
        try:
            res = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True)
            node_ver = res.stdout.strip()
            print(f"    -> [PASS] Node.js 런타임 확인: {node_ver}")
        except Exception:
            self.errors.append("시스템에 Node.js가 설치되어 있지 않거나 PATH에 없습니다. (프론트엔드 실행 시 필요)")
            all_ok = False

        # node_modules 확인
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            self.errors.append("frontend/node_modules 가 없습니다. 'npm install --prefix frontend' 실행이 필요합니다.")
            all_ok = False
        else:
            print("    -> [PASS] frontend/node_modules 종속성 확인 완료")

        if all_ok:
            self.passed_count += 1
        return all_ok

    def check_protected_files(self) -> bool:
        """5. 프로젝트 보호 파일 3종 SHA-256 무결성 검사"""
        print("[*] 기존 보호 자산 3종 SHA-256 무결성 검증...")
        all_ok = True
        for filename, expected_hash in PROTECTED_FILES.items():
            filepath = BASE_DIR / filename
            if not filepath.exists():
                self.errors.append(f"보호 파일이 누락되었습니다: {filename}")
                all_ok = False
                continue
            
            sha = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(65536):
                    sha.update(chunk)
            actual_hash = sha.hexdigest().upper()

            if actual_hash != expected_hash:
                self.errors.append(f"보호 파일 무결성 훼손: {filename} (기대: {expected_hash}, 실제: {actual_hash})")
                all_ok = False
            else:
                print(f"    -> [PASS] {filename} (SHA-256 100% 일치)")

        if all_ok:
            self.passed_count += 1
        return all_ok

    def run_all(self) -> int:
        print("=" * 65)
        print("  Franchise Dashboard 실행환경 사전점검 (Preflight Check)")
        print("=" * 65)

        self.check_python_version()
        self.check_python_dependencies()
        self.check_sqlite_databases()
        self.check_frontend_environment()
        self.check_protected_files()

        print("\n" + "=" * 65)
        print("  사전점검 결과 요약")
        print("=" * 65)

        if self.warnings:
            print(f"[경고 ({len(self.warnings)}건)] - 실행은 가능하나 확인을 권장합니다:")
            for w in self.warnings:
                print(f"  - {w}")

        if self.errors:
            print(f"[오류 ({len(self.errors)}건)] - 시스템 실행 전 해결이 필요합니다:")
            for e in self.errors:
                print(f"  - [X] {e}")
            print("\n[조치 가이드]")
            print("  1. Python 패키지 설치: pip install -r requirements.txt")
            print("  2. 프론트엔드 패키지 설치: npm install --prefix frontend")
            print("  3. DB 파일 무결성 및 data/ 디렉터리 경로를 확인하세요.")
            print("=" * 65)
            return 1

        print("[성공] 모든 핵심 실행환경 및 데이터 무결성 검증을 통과했습니다.")
        print("  -> 백엔드 실행: py -m uvicorn src.stage4e.api.main:app --port 8000")
        print("  -> 프런트엔드 실행: npm run dev --prefix frontend")
        print("  -> 스모크 테스트: py scripts/smoke_test_api.py")
        print("=" * 65)
        return 0


if __name__ == "__main__":
    checker = PreflightChecker()
    exit_code = checker.run_all()
    sys.exit(exit_code)

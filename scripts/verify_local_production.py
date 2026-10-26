"""Build and smoke-check the local production frontend and API without external writes."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
NPM = "npm.cmd" if os.name == "nt" else "npm"
NODE = "node.exe" if os.name == "nt" else "node"
VITE = ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
REPORT = ROOT / "reports" / "phase7_step2_local_production_validation.json"
DB = ROOT / "data" / "brand_master_v1.sqlite3"
PROTECTED = ("collector.py", "gangnam_food_stores.sqlite3", "run_gangnam.bat")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def database_snapshot() -> dict[str, object]:
    uri = DB.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        return {
            "size_bytes": DB.stat().st_size,
            "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
            "brands_count": connection.execute("SELECT COUNT(*) FROM brands").fetchone()[0],
            "links_count": connection.execute("SELECT COUNT(*) FROM store_brand_links").fetchone()[0],
            "reviews_count": connection.execute("SELECT COUNT(*) FROM brand_reviews").fetchone()[0],
        }


def assert_port_free(port: int) -> None:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"Port {port} is already in use") from exc


def wait_for(url: str, expected: bytes, timeout: float = 30.0) -> int:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=3) as response:
                body = response.read()
                if response.status == 200 and expected in body:
                    return response.status
        except Exception as exc:  # Server startup may briefly refuse connections.
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main() -> int:
    if not PYTHON.exists():
        raise RuntimeError(f"Project Python not found: {PYTHON}")
    for port in (8000, 4173):
        assert_port_free(port)

    before_db = database_snapshot()
    before_hashes = {name: sha256(ROOT / name) for name in PROTECTED}
    build_env = os.environ.copy()
    # 프로덕션 동일 출처(Same-Origin) 빌드 검증: VITE_API_URL을 빈 값("")으로 설정하여 상대 경로(/api/...) 요청을 보장
    build_env["VITE_API_URL"] = ""
    subprocess.run([NPM, "--prefix", "frontend", "run", "build"], cwd=ROOT, env=build_env, check=True)

    # 빌드된 정적 JS 파일에 127.0.0.1:8000/api 절대 경로가 남아있는지 엄격 검사
    dist_js_files = list((ROOT / "frontend" / "dist" / "assets").glob("*.js"))
    for js_file in dist_js_files:
        js_text = js_file.read_text(encoding="utf-8")
        if "http://127.0.0.1:8000/api" in js_text:
            raise RuntimeError(f"동일 출처 빌드 검증 실패: 절대 API 경로가 정적 번들에 포함됨: {js_file.name}")

    log_dir = ROOT / "reports"
    log_dir.mkdir(exist_ok=True)
    with (log_dir / "phase7_step2_backend.log").open("wb") as backend_log, (
        log_dir / "phase7_step2_frontend.log"
    ).open("wb") as frontend_log:
        backend = subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "src.stage4e.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT,
            stdout=backend_log,
            stderr=subprocess.STDOUT,
        )
        frontend = subprocess.Popen(
            [NODE, str(VITE), "preview", "--host", "127.0.0.1", "--port", "4173", "--strictPort"],
            cwd=ROOT / "frontend",
            stdout=frontend_log,
            stderr=subprocess.STDOUT,
        )
        try:
            api_status = wait_for("http://127.0.0.1:8000/", b'"status":"healthy"')
            frontend_status = wait_for("http://127.0.0.1:4173/", b'<div id="root"></div>')
            # 동일 출처 프록시 종단간(End-to-End) 검증:
            # 프론트엔드 출처(4173)를 통한 /api/v1/analytics/summary 호출 시 SPA fallback(HTML)이 아닌 실제 JSON 데이터가 반환되는지 확인
            same_origin_api_status = wait_for("http://127.0.0.1:4173/api/v1/analytics/summary", b'"total_stores":735185')
        finally:
            stop(frontend)
            stop(backend)

    after_db = database_snapshot()
    after_hashes = {name: sha256(ROOT / name) for name in PROTECTED}
    result = {
        "status": "PASS",
        "frontend_build": "PASS",
        "frontend_entrypoint": {"url": "http://127.0.0.1:4173/", "status_code": frontend_status},
        "api_health": {"url": "http://127.0.0.1:8000/", "status_code": api_status},
        "same_origin_api_proxy": {
            "url": "http://127.0.0.1:4173/api/v1/analytics/summary",
            "status_code": same_origin_api_status,
            "verified_json_payload": True,
        },
        "brand_master_before": before_db,
        "brand_master_after": after_db,
        "brand_master_unchanged": before_db == after_db,
        "protected_sha256_before": before_hashes,
        "protected_sha256_after": after_hashes,
        "protected_files_unchanged": before_hashes == after_hashes,
    }
    assert result["brand_master_unchanged"]
    assert result["protected_files_unchanged"]
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"LOCAL_PRODUCTION_OK: {REPORT}")
    return 0


if __name__ == "__main__":
    import traceback
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as error:
        print(f"LOCAL_PRODUCTION_FAILED: {error}", file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1)

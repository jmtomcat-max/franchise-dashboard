"""
Franchise Dashboard - 배포 템플릿(systemd, Nginx, Caddy, logging, backup) 정밀 파서 검증 스크립트
위치: scripts/verify_deployment_templates.py

검증 규칙:
1. Nginx: 블록 스택 추적, 세미콜론(;) 종결 강제, 지시어 화이트리스트 검사, 지시어별 최소 인수(Arguments) 개수 검사
2. Caddy: 블록 스택 추적, Caddyfile 키워드/지시어 화이트리스트 검사 (오타/임의 지시어 차단)
3. systemd: 섹션 구조 및 Key=Value 지시어 구문 검사
4. logging.conf: configparser ini 유효성 및 멀티프로세스 안전성(StreamHandler/journald) 검사
5. Python: ast.parse() 구문 트리 파싱
"""

from __future__ import annotations

import ast
import configparser
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPLOY_DIR = ROOT / "deploy"

# Nginx 표준 지시어 및 최소 필수 인수(arguments) 개수 매핑
NGINX_DIRECTIVES_MIN_ARGS = {
    "server": 0,             # 블록 전용
    "location": 1,           # 최소 경로 1개
    "listen": 1,             # 포트/주소
    "server_name": 1,        # 도메인
    "root": 1,               # 디렉터리 경로
    "index": 1,              # 인덱스 파일명
    "proxy_pass": 1,         # 대상 URL
    "proxy_set_header": 2,   # 헤더명 값
    "proxy_http_version": 1, # 버전
    "proxy_connect_timeout": 1,
    "proxy_read_timeout": 1,
    "proxy_send_timeout": 1,
    "proxy_buffering": 1,
    "proxy_buffer_size": 1,
    "proxy_buffers": 2,
    "try_files": 2,          # 최소 2개 이상의 fallback
    "add_header": 2,         # 헤더명 값
    "expires": 1,
    "access_log": 1,
    "error_log": 1,
    "ssl_certificate": 1,
    "ssl_certificate_key": 1,
    "ssl_protocols": 1,
    "ssl_ciphers": 1,
    "ssl_prefer_server_ciphers": 1,
    "ssl_session_cache": 1,
    "ssl_session_timeout": 1,
    "gzip": 1,
    "gzip_vary": 1,
    "gzip_proxied": 1,
    "gzip_comp_level": 1,
    "gzip_types": 1,
    "return": 1,
}

# Caddyfile 허용 키워드 및 지시어 화이트리스트
CADDY_ALLOWED_KEYWORDS = {
    # 사이트 주소
    "dashboard.example.com",
    # 블록 지시어
    "root", "file_server", "encode", "header", "handle", "reverse_proxy",
    "rewrite", "try_files", "log", "output", "roll_size", "roll_keep", "roll_keep_for",
    "header_up", "file",
    # 헤더 속성 키
    "X-Frame-Options", "X-Content-Type-Options", "X-XSS-Protection",
    "Referrer-Policy", "Strict-Transport-Security", "Cache-Control",
    # 매처 (matcher)
    "@static"
}


def parse_and_verify_nginx(content: str) -> dict:
    """Nginx 설정 파일의 토큰, 세미콜론 종결 규칙, 지시어 및 최소 인수 개수를 정밀 파싱 검증합니다."""
    lines = content.splitlines()
    stack = []
    directive_count = 0

    for line_no, raw_line in enumerate(lines, start=1):
        line = re.sub(r"#.*$", "", raw_line).strip()
        if not line:
            continue

        # 블록 열기
        if line.endswith("{"):
            header = line[:-1].strip()
            tokens = header.split()
            if not tokens:
                raise ValueError(f"[Line {line_no}] 블록 선언 누락: '{raw_line}'")
            directive = tokens[0]
            if directive not in NGINX_DIRECTIVES_MIN_ARGS:
                raise ValueError(f"[Line {line_no}] 알 수 없는 Nginx 블록 지시어: '{directive}'")
            min_args = NGINX_DIRECTIVES_MIN_ARGS[directive]
            args = tokens[1:]
            if len(args) < min_args:
                raise ValueError(f"[Line {line_no}] Nginx 블록 '{directive}' 인수 부족 (최소 {min_args}개 필요, 현재 {len(args)}개)")
            stack.append((directive, line_no))
            directive_count += 1
            continue

        # 블록 닫기
        if line == "}":
            if not stack:
                raise ValueError(f"[Line {line_no}] 매칭되지 않는 닫는 괄호 '}}'")
            stack.pop()
            continue

        # 일반 지시어는 반드시 세미콜론(;)으로 종결되어야 함
        if not line.endswith(";"):
            raise ValueError(f"[Line {line_no}] Nginx 지시어 세미콜론(;) 누락: '{line}'")

        stmt = line[:-1].strip()
        tokens = stmt.split()
        if not tokens:
            continue

        directive = tokens[0]
        if directive not in NGINX_DIRECTIVES_MIN_ARGS:
            raise ValueError(f"[Line {line_no}] 알 수 없는 Nginx 지시어: '{directive}'")

        min_args = NGINX_DIRECTIVES_MIN_ARGS[directive]
        args = tokens[1:]
        if len(args) < min_args:
            raise ValueError(f"[Line {line_no}] Nginx 지시어 '{directive}' 인수 누락/부족 (최소 {min_args}개 필요, 현재 {len(args)}개): '{stmt}'")

        directive_count += 1

    if stack:
        unclosed = [f"{d}(line {ln})" for d, ln in stack]
        raise ValueError(f"닫히지 않은 Nginx 블록 존재: {unclosed}")

    return {
        "status": "PASS",
        "directives_verified": directive_count,
        "parser": "nginx_ast_tokenizer_v2"
    }


def parse_and_verify_caddy(content: str) -> dict:
    """Caddyfile의 블록 중첩 및 토큰 화이트리스트를 정밀 파싱 검증합니다."""
    lines = content.splitlines()
    stack = []
    directive_count = 0

    for line_no, raw_line in enumerate(lines, start=1):
        line = re.sub(r"#.*$", "", raw_line).strip()
        if not line:
            continue

        # 닫는 괄호 단독
        if line == "}":
            if not stack:
                raise ValueError(f"[Line {line_no}] Caddy 매칭되지 않는 닫는 괄호 '}}'")
            stack.pop()
            continue

        # 토큰 분리
        stmt = line[:-1].strip() if line.endswith("{") else line
        tokens = stmt.split()
        if not tokens:
            continue

        first_token = tokens[0]
        if first_token not in CADDY_ALLOWED_KEYWORDS:
            raise ValueError(f"[Line {line_no}] 알 수 없는 Caddy 지시어/속성 키워드: '{first_token}'")

        if line.endswith("{"):
            stack.append((first_token, line_no))

        directive_count += 1

    if stack:
        unclosed = [f"{d}(line {ln})" for d, ln in stack]
        raise ValueError(f"닫히지 않은 Caddy 블록 존재: {unclosed}")

    return {
        "status": "PASS",
        "directives_verified": directive_count,
        "parser": "caddy_token_whitelist_v2"
    }


def parse_and_verify_systemd(content: str) -> dict:
    """systemd 서비스 유닛 파일의 섹션 및 Key=Value 문법을 정밀 파싱합니다."""
    lines = content.splitlines()
    sections = {}
    current_sec = None

    for line_no, raw_line in enumerate(lines, start=1):
        line = re.sub(r"^[#;].*$", "", raw_line).strip()
        if not line:
            continue

        if line.startswith("[") and line.endswith("]"):
            current_sec = line[1:-1].strip()
            if not current_sec:
                raise ValueError(f"[Line {line_no}] 잘못된 섹션 선언: {raw_line}")
            sections.setdefault(current_sec, {})
            continue

        if "=" in line:
            if current_sec is None:
                raise ValueError(f"[Line {line_no}] 섹션 없는 지시어: {raw_line}")
            key, _, val = line.partition("=")
            sections[current_sec][key.strip()] = val.strip()
        elif line.endswith("\\"):
            pass
        else:
            raise ValueError(f"[Line {line_no}] 잘못된 systemd 지시어 구문: '{raw_line}'")

    for req in ("Unit", "Service", "Install"):
        if req not in sections:
            raise ValueError(f"systemd 필수 섹션 누락: [{req}]")

    service = sections["Service"]
    for req_key in ("ExecStart", "WorkingDirectory", "User", "Group", "Restart"):
        if req_key not in service:
            raise ValueError(f"systemd [Service] 필수 키 누락: {req_key}")

    return {
        "status": "PASS",
        "sections": list(sections.keys()),
        "service_keys_count": len(service),
        "parser": "systemd_unit_parser_v2"
    }


def verify_all_templates() -> dict:
    """모든 배포 구성 파일에 대한 정밀 검증을 수행합니다."""
    results = {}

    # 1. Nginx 검증 (지시어 + 인수 + 세미콜론) - 메인 HTTPS 및 초기 HTTP 부트스트랩
    nginx_path = DEPLOY_DIR / "nginx.conf"
    results["nginx_conf"] = parse_and_verify_nginx(nginx_path.read_text(encoding="utf-8"))

    nginx_boot_path = DEPLOY_DIR / "nginx-bootstrap.conf"
    results["nginx_bootstrap_conf"] = parse_and_verify_nginx(nginx_boot_path.read_text(encoding="utf-8"))

    # 2. Caddyfile 검증 (지시어/속성 화이트리스트 + 블록)
    caddy_path = DEPLOY_DIR / "Caddyfile"
    results["caddyfile"] = parse_and_verify_caddy(caddy_path.read_text(encoding="utf-8"))

    # 3. systemd 유닛 검증
    service_path = DEPLOY_DIR / "franchise-dashboard.service"
    results["systemd_unit"] = parse_and_verify_systemd(service_path.read_text(encoding="utf-8"))

    # 4. logging.conf 검증 (StreamHandler / journald 전용 안전성 확인)
    log_path = DEPLOY_DIR / "logging.conf"
    cfg = configparser.ConfigParser()
    cfg.read(str(log_path), encoding="utf-8")
    if "handler_file" in cfg.sections() or "RotatingFileHandler" in log_path.read_text(encoding="utf-8"):
        raise ValueError("logging.conf에 멀티프로세스 충돌 위험이 있는 RotatingFileHandler가 남아있음")
    if "handler_console" not in cfg.sections():
        raise ValueError("logging.conf에 journald/stdout 수집용 handler_console 누락")
    results["logging_conf"] = {
        "status": "PASS",
        "sections": list(cfg.sections()),
        "multiprocess_safe": True
    }

    # 5. 파이썬 배포 보조 스크립트 구문 검증
    scripts = ["backup_production_db.py", "verify_local_production.py"]
    script_results = {}
    for s_name in scripts:
        s_path = ROOT / "scripts" / s_name
        ast.parse(s_path.read_text(encoding="utf-8"), filename=str(s_path))
        script_results[s_name] = "SYNTAX_OK"
    results["python_syntax"] = {
        "status": "PASS",
        "scripts": script_results
    }

    return results


def main():
    print("=" * 70)
    print(" Franchise Dashboard 배포 구성 템플릿 정밀 파서 및 정합성 검증")
    print("=" * 70)

    try:
        results = verify_all_templates()
        for name, res in results.items():
            print(f"[PASS] {name:<22} | {res}")
        print("=" * 70)
        print("[성공] 모든 배포 템플릿이 정밀 파서 규칙(지시어, 인수 최소수, 세미콜론, 블록, ini)을 통과했습니다.")
        return 0
    except Exception as exc:
        print(f"[실패] 템플릿 정밀 파서 검증 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

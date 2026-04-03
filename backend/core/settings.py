"""
Commercial web runtime settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = PROJECT_ROOT / ".env"

DEFAULT_FRONTEND_PORT_CANDIDATES = list(range(4173, 4191)) + list(range(5173, 5186))


def _load_env_file() -> None:
    if not ENV_FILE_PATH.exists():
        return

    for raw_line in ENV_FILE_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _get_csv(name: str, default: Iterable[str]) -> List[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _get_port_candidates(name: str, default: List[int]) -> List[int]:
    values = []
    for item in _get_csv(name, [str(value) for value in default]):
        try:
            values.append(int(item))
        except ValueError:
            continue
    return values or list(default)


_load_env_file()

COMMERCIAL_ENV = os.getenv("COMMERCIAL_ENV", "development").strip() or "development"
COMMERCIAL_DB_PATH = os.getenv("COMMERCIAL_DB_PATH", "").strip()
COMMERCIAL_PAYMENT_WEBHOOK_SECRET = os.getenv("COMMERCIAL_PAYMENT_WEBHOOK_SECRET", "").strip()
COMMERCIAL_MANUAL_TRANSFER_ACCOUNT_NAME = os.getenv("COMMERCIAL_MANUAL_TRANSFER_ACCOUNT_NAME", "AI Novel Generator 商业版").strip() or "AI Novel Generator 商业版"
COMMERCIAL_MANUAL_TRANSFER_ACCOUNT_NO = os.getenv("COMMERCIAL_MANUAL_TRANSFER_ACCOUNT_NO", "6222-0000-0000-0000").strip() or "6222-0000-0000-0000"
COMMERCIAL_MANUAL_TRANSFER_BANK_NAME = os.getenv("COMMERCIAL_MANUAL_TRANSFER_BANK_NAME", "示例银行上海分行").strip() or "示例银行上海分行"

COMMERCIAL_BACKEND_HOST = os.getenv("COMMERCIAL_BACKEND_HOST", "127.0.0.1").strip() or "127.0.0.1"
COMMERCIAL_BACKEND_BIND_HOST = os.getenv("COMMERCIAL_BACKEND_BIND_HOST", COMMERCIAL_BACKEND_HOST).strip() or COMMERCIAL_BACKEND_HOST
COMMERCIAL_BACKEND_PORT = _get_int("COMMERCIAL_BACKEND_PORT", 8000)
COMMERCIAL_BACKEND_URL = os.getenv(
    "COMMERCIAL_BACKEND_URL",
    f"http://{COMMERCIAL_BACKEND_HOST}:{COMMERCIAL_BACKEND_PORT}",
).strip() or f"http://{COMMERCIAL_BACKEND_HOST}:{COMMERCIAL_BACKEND_PORT}"

COMMERCIAL_FRONTEND_HOST = os.getenv("COMMERCIAL_FRONTEND_HOST", "127.0.0.1").strip() or "127.0.0.1"
COMMERCIAL_FRONTEND_BIND_HOST = os.getenv("COMMERCIAL_FRONTEND_BIND_HOST", COMMERCIAL_FRONTEND_HOST).strip() or COMMERCIAL_FRONTEND_HOST
COMMERCIAL_FRONTEND_PORT = _get_int("COMMERCIAL_FRONTEND_PORT", 4173)
COMMERCIAL_FRONTEND_PORT_CANDIDATES = _get_port_candidates(
    "COMMERCIAL_FRONTEND_PORT_CANDIDATES",
    DEFAULT_FRONTEND_PORT_CANDIDATES,
)

COMMERCIAL_CORS_ORIGINS = _get_csv(
    "COMMERCIAL_CORS_ORIGINS",
    [
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
)

COMMERCIAL_AUDIT_LOG_LIMIT = _get_int("COMMERCIAL_AUDIT_LOG_LIMIT", 100)

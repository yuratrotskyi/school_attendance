"""Runtime configuration loading utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import os
from pathlib import Path
from typing import Dict, Optional, Set


@dataclass
class AppConfig:
    nz_login: Optional[str]
    nz_password: Optional[str]
    semester_start: date
    risk_threshold: float
    excused_codes: Set[str]
    data_dir: Path
    out_dir: Path
    logs_dir: Path
    selectors_path: Optional[Path]
    base_url: str


def load_config(env_file: Optional[Path] = None) -> AppConfig:
    if env_file is None:
        env_file = Path(".env")

    if env_file.exists():
        _load_dotenv(env_file)

    semester_start_text = os.getenv("SEMESTER_START", "2026-01-12")
    semester_start = datetime.strptime(semester_start_text, "%Y-%m-%d").date()

    threshold_text = os.getenv("RISK_THRESHOLD", "0.10")
    risk_threshold = float(threshold_text)

    excused = os.getenv(
        "EXCUSED_CODES",
        "EXCUSED_MEDICAL,EXCUSED_FAMILY,EXCUSED_ADMIN",
    )
    excused_codes = {item.strip() for item in excused.split(",") if item.strip()}

    return AppConfig(
        nz_login=os.getenv("NZ_LOGIN"),
        nz_password=os.getenv("NZ_PASSWORD"),
        semester_start=semester_start,
        risk_threshold=risk_threshold,
        excused_codes=excused_codes,
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        out_dir=Path(os.getenv("OUT_DIR", "out")),
        logs_dir=Path(os.getenv("LOGS_DIR", "logs")),
        selectors_path=Path(os.getenv("SELECTORS_PATH")) if os.getenv("SELECTORS_PATH") else None,
        base_url=os.getenv("NZ_BASE_URL", "https://nz.ua"),
    )


def _load_dotenv(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

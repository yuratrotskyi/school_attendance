"""Runtime configuration loading utilities."""

from dataclasses import dataclass
import os
from typing import Optional


@dataclass
class AppConfig:
    nz_login: Optional[str]
    nz_password: Optional[str]


def load_config() -> AppConfig:
    return AppConfig(
        nz_login=os.getenv("NZ_LOGIN"),
        nz_password=os.getenv("NZ_PASSWORD"),
    )

"""Class name normalization helpers."""

from __future__ import annotations

import re


def normalize_class_name(raw: str) -> str:
    """Normalize class names by removing parenthesized suffixes."""

    text = " ".join(str(raw or "").split())
    if not text:
        return ""

    text = re.sub(r"\s*\([^)]*\)\s*$", "", text)
    return " ".join(text.split()).strip()

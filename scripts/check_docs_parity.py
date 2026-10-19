#!/usr/bin/env python
"""Check that English and Chinese docs have the same file set and are non-empty."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    en = ROOT / "docs" / "en"
    zh = ROOT / "docs" / "zh"
    errors: list[str] = []
    if not en.is_dir() or not zh.is_dir():
        print("docs/en or docs/zh is missing", file=sys.stderr)
        return 1
    en_files = {path.name for path in en.glob("*.md")}
    zh_files = {path.name for path in zh.glob("*.md")}
    missing_zh = sorted(en_files - zh_files)
    missing_en = sorted(zh_files - en_files)
    if missing_zh:
        errors.append(f"missing Chinese translations: {missing_zh}")
    if missing_en:
        errors.append(f"missing English originals: {missing_en}")
    for directory in (en, zh):
        for path in sorted(directory.glob("*.md")):
            if path.stat().st_size < 100:
                errors.append(f"placeholder/empty doc: {path.relative_to(ROOT)}")
    for name in ("README.md", "README_CN.md"):
        path = ROOT / name
        if not path.exists() or path.stat().st_size < 100:
            errors.append(f"missing or too small: {name}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"docs parity OK: {len(en_files)} English / {len(zh_files)} Chinese files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

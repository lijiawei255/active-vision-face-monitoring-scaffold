#!/usr/bin/env python
"""Check relative Markdown links in the repository documentation."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {".git", "var", "dist", "build", ".ruff_cache", ".pytest_cache", "__pycache__"}


def markdown_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*.md"):
        if any(part in EXCLUDE for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def main() -> int:
    errors: list[str] = []
    files = markdown_files()
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)} -> {target}")
    if errors:
        print("Broken relative links:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    print(f"Markdown links OK ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Allow ``python -m avfm``."""

from __future__ import annotations

from avfm.cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

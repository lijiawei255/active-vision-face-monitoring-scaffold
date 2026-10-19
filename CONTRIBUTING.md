# Contributing

Thanks for considering a contribution. This project is a small, hardware-agnostic scaffold; the
most valuable contributions are reproducible bug reports, contract/SIL tests, and documentation
corrections.

## Setup

```bash
conda create -n avfm python=3.11 -c conda-forge -y
conda run -n avfm python -m pip install -e ".[dev,mediapipe]"
conda run -n avfm avfm models download --all
```

Windows: `scripts/bootstrap.ps1`. Linux: `scripts/bootstrap.sh`.

## Before opening a PR

```bash
conda run -n avfm ruff check src tests
conda run -n avfm ruff format --check src tests
conda run -n avfm python -m mypy
conda run -n avfm python -m pytest -m "not webcam and not hardware and not mediapipe" \
  --cov=avfm --cov-fail-under=80
conda run -n avfm python scripts/check_docs_parity.py
```

If you change dependencies, regenerate the locked files under `requirements/` with the commands
in [docs/en/testing.md](docs/en/testing.md#dependency-locks) — CI fails when they are stale.

## Rules

- Keep the hardware-agnostic boundaries: capture / detection / perception / metrics / fatigue /
  control / actuation. Do not hard-code a specific camera or servo into the core.
- A new backend needs a contract test and, if it affects control, a SIL or replay test.
- Do not claim hardware verification unless you actually ran `scripts/rpi_smoke.py` or
  `scripts/rpi_bench.py` on that hardware and attached the JSON.
- Update both `docs/en` and `docs/zh` for user-facing changes.
- **Do not commit** `.env`, API keys, personal face images/videos, downloaded models or run
  artifacts. The only face image in the repository is the public-domain NASA test fixture.
- Keep default configuration safe: `actuator.backend = "none"` on desktop; Pi users opt into
  `pca9685`/`auto`.

## Commit style

Conventional Commits, e.g.:

```text
feat(control): add rate-limited search sweep
fix(fatigue): reject EAR samples when the head is turned
docs: update bilingual hardware guide
test(cadence): cover split detector reuse
```

## Reporting privacy/security issues

Do not open a public issue with face images, recordings or credentials. Use GitHub Security
Advisories; see [SECURITY.md](SECURITY.md).

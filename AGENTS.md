# AGENTS.md — project guide for AI-assisted development

This is the project-level workspace instruction file for DeepSeek Harness (and other coding
agents). It complements the user-level `~/.dsh/AGENTS.md`: user-level preferences (language,
tooling, GitHub conventions) always win over anything here.

## TL;DR

- Stack: Python 3.11, NumPy, OpenCV 5 (required), optional MediaPipe Tasks, optional Raspberry Pi
  stack (Picamera2 + PCA9685 via ServoKit). Package name: `avfm`.
- Run everything through the conda env: `conda run -n avfm ...`. Never use the system Python for
  project work.
- A change is done only when the local gate passes — `scripts/run_checks.ps1` plus the MediaPipe
  run and lock-file check in [Definition of done](#definition-of-done).
- Raspberry Pi hardware (camera + servos) is **contract-tested only**. Never present SIL, mock or
  contract tests as hardware evidence.

## What this repo is

`avfm` is a hardware-agnostic reference scaffold for 2-DOF PID gimbal face tracking and real-time
fatigue monitoring (EAR, blink/microsleep, PERCLOS, head-pose distraction). MIT licensed. It is a
reference architecture, not a product, not face recognition, and not a certified DMS.

Verified: desktop SIL, synthetic and real detector fixtures, Windows webcam passive run, annotated
video, package smoke test. Not verified: Raspberry Pi 5 Picamera2/PCA9685/servo path (HIL pending).

Explicit non-goals: face recognition/identity/embeddings, cloud upload, hosted dashboard,
medical/safety certification, turnkey end-user app.

## Start of session (cheap sanity checks)

```bash
git status --short
conda run -n avfm avfm doctor --json        # capabilities without touching hardware
conda run -n avfm avfm selftest --quick     # SIL regression, ~2 s
```

If models are missing: `conda run -n avfm avfm models download --all`.

## Environment

```bash
conda create -n avfm python=3.11 -c conda-forge -y
conda run -n avfm python -m pip install -e ".[dev,mediapipe]"
conda run -n avfm avfm models download --all
conda run -n avfm avfm selftest
```

- Extras: `dev` (pytest, ruff, mypy, pre-commit, build, twine), `mediapipe`, `rpi` (Linux only:
  `picamera2`, `adafruit-circuitpython-servokit`).
- Models are **not committed**. URLs + SHA-256 live in `src/avfm/models.py`; offline work uses
  `--model-dir` or `AVFM_MODEL_DIR`.
- Bootstrap helpers: `scripts/bootstrap.ps1` (Windows), `scripts/bootstrap.sh` (Linux).
- CLI: `run`, `simulate`, `replay`, `detect`, `calibrate ear`, `doctor`, `selftest`,
  `models download|verify`, `info`. `avfm run --dry-run --json` prints the fully resolved config.

## Definition of done

```bash
conda run -n avfm python -m ruff check src tests
conda run -n avfm python -m ruff format --check src tests
conda run -n avfm python -m mypy
conda run -n avfm python -m pytest -m "not webcam and not hardware and not mediapipe" \
  --cov=avfm --cov-fail-under=80
conda run -n avfm python -m pytest -m "mediapipe or model" --run-mediapipe --no-cov
conda run -n avfm python scripts/check_docs_parity.py
conda run -n avfm python scripts/check_docs_links.py
```

- `mypy` checks `src/` only (configured in `pyproject.toml`). `warn_unused_ignores` is on, so every
  `# type: ignore[...]` must be genuinely required; currently only two (dynamic handler attributes
  in `logging.py`, both documented).
- Coverage gate is 80%; the suite is around 88% (roughly 240 core tests).
- `scripts/run_checks.ps1` is the Windows fast path (ruff + mypy + docs + core tests + selftest).
  It does not replace the MediaPipe run above.
- If you changed dependencies, regenerate the lock files (see [CI and dependencies](#ci-and-dependencies)).

## Architecture and invariants

Layers: `capture → detection → perception → metrics → control/fatigue → actuation → app`.
`cli.py` wires it together. Keep this layering: do not hard-code a camera or servo into the core.

Invariants (do not break without updating docs and tests):

- `Frame.image` is BGR `uint8` `(H, W, 3)`; `BBox` is normalised to `[0, 1]` with a top-left origin.
- PID output is degrees/second; `dt` is seconds; angles are degrees; timestamps are monotonic
  seconds (video sources use `index / file_fps`).
- EAR is computed in **pixel space** — normalised coordinates distort the ratio on non-square frames.
- Head pose uses the **outer** eye corners (landmarks 33/263); the inner corners produced a ~50°
  yaw bias (fixed in 0.1.1).
- MediaPipe expects RGB; the wrapper converts from the project-wide BGR contract.
- The pipeline is **single-threaded and deterministic**. A frame is captured, perceived, tracked,
  fatigue-analysed, actuated and optionally recorded before the next one. Do not introduce hidden
  threads or async into the core; it breaks replay and SIL determinism.
- Optional dependencies (`mediapipe`, `picamera2`, `adafruit_servokit`) must be imported **lazily**
  inside functions. `import avfm` must work with NumPy + OpenCV only.
- Detection cadence: `single` or `split` (fast tracking detector + slower landmark detector). The
  tracker PID runs every frame using the last observation within `tracker.hold_last_s`; PERCLOS
  samples only frames where the fatigue detector actually ran (skipped frames are not "eyes open").
- Passive mode (`--servo none`) is first-class: desired angles are computed/logged, physical search
  never runs, `FACE_LOST` is reported honestly.
- `auto` actuator/detector fallbacks must be logged, written to `run.json`, and visible in `doctor`;
  never degrade silently.
- `FatigueSnapshot.state` / `TrackerState` are the observable contract consumed by overlay/recorder.

## Configuration

- Dataclass defaults in `src/avfm/config.py` are canonical. `configs/default.toml` mirrors them for
  documentation; profiles contain **only overrides** and are deep-merged.
- Unknown TOML keys are an error (`ConfigError`), and every value has range validation.
- Adding a knob: dataclass field → `validate()` → update `configs/default.toml` → add a case to
  `tests/unit/test_config_validation.py`. Cross-field constraints go into `AppConfig.validate`.
- `configs/demo_short.toml` is demo-only (10/15 s acceleration). Normal profiles must never load it.
- Env vars: `AVFM_CONFIG` (extra config path), `AVFM_MODEL_DIR` (model root).

## Testing

- Markers: `model`, `mediapipe`, `webcam`, `hardware`, `slow`. Opt-in flags: `--run-mediapipe`,
  `--run-webcam`, `--run-hardware`. Global `--timeout=60` from `pyproject.toml`.
- Synthetic geometry helpers live in `tests/helpers.py` (`make_frame`, `make_eye_landmarks`,
  `make_head_pose_landmarks`, `make_metrics`, `make_observation`). Note: `tests/conftest.py` and
  `tests/helpers.py` duplicate the pytest hooks/fixtures — update **both** if you touch them.
- A new backend needs a contract test; if it affects control, add a SIL (`avfm simulate`) or replay
  test. Prefer `FakeDetector`, `ListSource`-style fakes and `monkeypatch` over real devices.
- Hardware/camera tests must stay opt-in. CI must never require a camera, servos or a display.
- Only `tests/data/astronaut.jpg` (public-domain NASA image) may be committed. Never add real face
  images, recordings or personal data.
- Do not claim hardware verification without `scripts/rpi_smoke.py` / `scripts/rpi_bench.py` output.

## CI and dependencies

`.github/workflows/ci.yml` has four jobs: `lint`, `core` (ubuntu + windows), `mediapipe`
(ubuntu + windows), `package` (wheel build + clean-venv smoke). CI is pinned to
`uv 0.11.3` (`UV_VERSION`) and `astral-sh/setup-uv@v7`.

- CI installs from hashed lock files and never resolves ranges at run time:
  `requirements/lock-core.txt`, `lock-dev.txt`, `lock-dev-mediapipe.txt`, followed by
  `uv pip install --system -e . --no-deps`.
- The lint job regenerates the locks and fails on `git diff` drift. After **any** dependency change:

```bash
uv pip compile pyproject.toml --universal --python-version 3.11 --generate-hashes \
  -o requirements/lock-core.txt
uv pip compile pyproject.toml --extra dev --universal --python-version 3.11 \
  --generate-hashes -o requirements/lock-dev.txt
uv pip compile pyproject.toml --extra dev --extra mediapipe --universal \
  --python-version 3.11 --generate-hashes -o requirements/lock-dev-mediapipe.txt
```

- `uv.lock` **cannot** be used here: the `rpi` extra pulls Linux-only `picamera2` →
  `python-prctl`/`pidng`, which have no wheels and no buildable metadata on non-Linux hosts, so a
  universal `uv lock` fails. Keep the hashed-requirements approach.
- MediaPipe on headless Linux needs `libegl1 libgles2` (installed in the workflow). The mediapipe
  job runs with `--run-mediapipe`, i.e. the real landmarker tests.
- The package job installs the built wheel against `lock-core.txt` and runs `avfm selftest`,
  `avfm doctor --json`, `avfm --version`.

## Recipes for common changes

1. **New detector backend**: implement `FaceDetector` (`detect`, `close`, `name`,
   `supports_landmarks`) under `src/avfm/detection/`, register it in `factory.py` and the config
   enum, lazy-import optional packages, add contract tests, update `docs/en|zh/architecture.md` and
   `configs/default.toml`.
2. **New servo backend**: implement `Servo` (`can_move`, `physical`, `set_angle`, `get_angle`,
   `close`) under `src/avfm/actuation/`, wire `factory.create_actuator` including
   `none | mock | auto` fallback semantics, contract-test with a fake ServoKit, update
   `docs/en|zh/hardware.md`.
3. **New metric (e.g. MAR/yawn)**: pure function + dataclass in `src/avfm/metrics/`, wire through
   `compute_face_metrics`, consume in `fatigue/monitor.py`, unit-test with synthetic landmarks.
4. **Control changes**: adjust `control/pid.py`, `gimbal.py` or `tracker.py`, then verify with
   `avfm simulate --scenario step|sine|lost|noisy`, `avfm selftest`, and update
   `docs/en|zh/control.md`.
5. **Output/recording changes**: the JSONL schema lives in `app/recorder.py` and `app/replay.py`;
   update both plus the "Session format" section of `docs/en|zh/architecture.md`.
6. **Docs changes**: every user-facing doc needs EN + ZH (filename sets are checked by
   `check_docs_parity.py`); relative links are checked by `check_docs_links.py`.

## Traps (learned the hard way)

- OpenCV 5 removed `cv2.CascadeClassifier` from core and no longer ships `cv2.data/haarcascades`.
  Use `cv2.FaceDetectorYN` (YuNet) — do not reintroduce Haar.
- MediaPipe 0.10.31+ removed `mp.solutions`. Use `mp.tasks.vision.FaceLandmarker` with the
  downloaded `.task` model.
- `cv2.VideoWriter_fourcc` is missing from the type stubs — use `cv2.VideoWriter.fourcc(...)`.
- Windows PowerShell 5.1 has no `&&`; use `;` or separate commands. Prefer `conda run -n avfm`.
- The reference Pi camera is mounted upside-down → `flip = "vertical"` in `configs/rpi.toml`.
- Servo limits are build-specific (pan 40–180°, tilt 0–140° in the reference build). Servos need an
  external 5 V supply with a common ground; never power them from the Pi 5 V rail.
- `PCA9685Servo._KIT_CACHE` is a process-wide ServoKit cache; tests use `clear_kit_cache()`. Do not
  replace it with per-instance board opens without hardware testing.
- `run.json` deliberately drops absolute `loaded_from` paths; do not reintroduce them.
- Recording is opt-in and JSONL must never contain raw pixels. Keep the privacy defaults intact.
- `var/` holds run artifacts (gitignored); never commit sessions, videos or calibration files.
- Model URLs/SHA-256 are duplicated in `src/avfm/models.py` and `docs/en|zh/architecture.md`;
  update all three together (and `THIRD_PARTY_LICENSES.md` when licenses change).

## Versioning and release

- The version appears in `pyproject.toml`, `src/avfm/__init__.py` (fallback), and `CITATION.cff`.
  Bump all three together; `CHANGELOG.md` follows Keep a Changelog.
- PyPI publication is not done yet (`avfm` name is available). Local packaging check:
  `python -m build && twine check dist/*`.
- Commit style: Conventional Commits (`fix:`, `test:`, `ci:`, `docs:`). Never commit models, face
  data, recordings or secrets.

## Where to read first

1. [README.md](README.md) — overview, operating modes, verification matrix.
2. [docs/en/architecture.md](docs/en/architecture.md) — contracts, cadence, models, session format.
3. [docs/en/testing.md](docs/en/testing.md) — test pyramid, markers, lock files, HIL checklist.
4. [docs/en/control.md](docs/en/control.md) and [docs/en/fatigue.md](docs/en/fatigue.md) before
   touching PID gains or fatigue thresholds.

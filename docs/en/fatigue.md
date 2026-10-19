# Fatigue indicators

> These are heuristic indicators, not a medical diagnosis and not a certified driver-monitoring
> system. PERCLOS is a research metric; its implementation and thresholds vary across studies.

## EAR (Eye Aspect Ratio)

For each eye, using six MediaPipe landmarks:

```text
EAR = (|p1-p5| + |p2-p4|) / (2 * |p0-p3|)
```

The calculation uses pixel coordinates, not normalised coordinates, so a 640×480 frame does not
distort the ratio. If one eye is invalid, the other is used; if both are invalid the frame is
marked invalid for fatigue.

- Default threshold: 0.2.
- `avfm calibrate ear` collects open-eye samples and sets
  `threshold = clip(median * ratio, floor, ceiling)`.
- Typical values depend on the person, glasses, lighting and camera angle; recalibrate when those
  change.

## Blink, microsleep and PERCLOS

- **Blink**: closed duration between `blink_min_s` (0.05 s) and `blink_max_s` (0.4 s), then open.
- **Microsleep**: continuous closure ≥ `microsleep_s` (1.5 s) → `DROWSY`.
- **PERCLOS**: rolling `perclos_window_s` (60 s) fraction of valid samples whose EAR was below
  threshold. It requires:
  - `perclos_warmup_s` (30 s) of history;
  - `perclos_min_coverage` (0.8) of valid samples;
  - a sample no older than `perclos_max_gap_s` (0.5 s).
- A 0.4–1.5 s closure is neither a blink nor an immediate microsleep; it contributes to PERCLOS.

Invalid samples (no face, no landmarks, pose-gated EAR) are stored as invalid so missing data
cannot look like alertness. `perclos_ready=False` means "not enough data", not "alert".

## Head pose and pose gating

Six 3D model points (nose, chin, eye inner corners, mouth corners) are matched to six MediaPipe
landmarks with `cv2.solvePnP` (SQPNP first, iterative fallback). A pose is valid only if the mean
reprojection error is below `max_reproj_error_px`.

- Looking away: `|yaw| > distraction_yaw_deg` (20°) or `|pitch| > distraction_pitch_deg` (15°)
  for `distraction_confirm_s` (2 s) → `DISTRACTED`. The `desktop` profile raises the pitch
  threshold to 25° because laptop cameras are often below eye level.
- Pose-gated EAR: when `|yaw| > ear_max_yaw_deg` (25°) or `|pitch| > ear_max_pitch_deg` (20°),
  the EAR/PERCLOS sample is marked invalid. This avoids false "closed eyes" when the face is
  turned away. The `desktop` profile uses 25° for pitch as well.

The camera intrinsic matrix is approximated from `camera.hfov_deg` (default 60°) with a square
pixel assumption. For precise pose, calibrate the camera and provide `fx/fy/cx/cy`. The coarse
thresholds above are intentionally tolerant.

## State machine

Priority: `DROWSY` > `DISTRACTED` > `ALERT`; `NO_FACE` when the face has been absent for
`face_lost_s`; `UNAVAILABLE` when MediaPipe/fatigue is disabled or missing.

- Enter/exit hysteresis use `recovery_s`.
- Events have `event_cooldown_s` to avoid spam.
- Events: `DROWSY_STARTED/ENDED`, `DISTRACTED_STARTED/ENDED`, `BLINK`.

## PERCLOS references

- Wierwille et al. (1994), PERCLOS definition as the proportion of time the eyes are at least 80%
  closed.
- FHWA/NHTSA Tech Brief, "PERCLOS: A Valid Psychophysiological Measure of Alertness".
- Abe et al., "PERCLOS-based technologies for detecting drowsiness: current evidence and future
  directions", SLEEP Advances (2023) — discusses the variability of definitions and thresholds.

This project uses an EAR proxy for eyelid closure, not an 80%-pupil-occlusion measurement. That is
a deliberate engineering compromise for a webcam/Pi scaffold.

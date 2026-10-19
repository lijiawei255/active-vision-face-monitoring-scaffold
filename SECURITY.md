# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Yes (alpha) |

## Reporting a vulnerability

Please **do not** open a public issue for security or privacy problems. Use GitHub Security
Advisories ("Report a vulnerability" on the repository Security tab) or contact the maintainer
through GitHub.

Include:

- affected version/commit and platform;
- a minimal reproduction (no personal data);
- impact (e.g., camera data exposure, unsafe actuator command, path traversal in a config).

## Privacy-sensitive reports

Do not attach face images, recordings, API keys or personal data. Replace them with synthetic
examples or the public-domain test fixture.

## Runtime security model

- No network access at runtime; frames are processed locally.
- No face recognition or identity database.
- Recording is off by default; `--record-video` is explicit.
- CI uses `contents: read` and no secrets.
- Downloaded models are verified with SHA-256 before use.
- `auto` actuator probe failures fall back to passive mode and are logged, not hidden.

## Known limitations

- This project is not a medical device or a safety-certified driver-monitoring system.
- Fatigue indicators are heuristic and can produce false positives/negatives.
- Servo power, mechanical limits and emergency stop are the builder's responsibility.

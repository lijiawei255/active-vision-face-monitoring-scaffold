# Hardware reference

This is the reference build derived from the parent project. Other pan/tilt mechanisms work if you
implement the `Servo` protocol (see [porting.md](porting.md)).

## Bill of materials

| Part | Role | Connection |
|---|---|---|
| Raspberry Pi 5 | host | — |
| OV5647 CSI camera | frames | MIPI CSI-2, 15-pin FPC |
| PCA9685 | 16-channel PWM driver | I2C address 0x40, SDA GPIO2 (pin 3), SCL GPIO3 (pin 5) |
| SG90 pan servo | horizontal | PCA9685 CH2 |
| SG90 tilt servo | vertical | PCA9685 CH3 |
| External 5V ≥2A supply | servo power | common ground with Pi |
| Cooling | Pi 5 thermal | heatsink/fan recommended |

## Wiring and power

- PCA9685 VCC from the **external 5V supply**, not the Pi 5V rail.
- Common ground between PCA9685, servo supply and Pi.
- Servo signal wires to CH2 (pan) and CH3 (tilt).
- Check I2C before running: `sudo i2cdetect -y 1` must show `0x40`.
- Keep the CSI cable clear of the moving gimbal; add strain relief.

## Reference limits

| Axis | Minimum | Maximum | Default/park |
|---|---:|---:|---:|
| Pan | 40° | 180° | 90° |
| Tilt | 0° | 140° | 80° |

The parent hardware used these limits to avoid pulling the camera cable. Your mechanism may differ;
change `[gimbal]` and `[tracker]` in the profile.

## Camera mounting

The reference camera is mounted upside-down, so `configs/rpi.toml` sets:

```toml
[camera]
source = "picamera"
flip = "vertical"
```

For a normally mounted camera use `flip = "none"`. If pan/tilt directions are reversed, set
`tracker.invert_pan` / `tracker.invert_tilt` rather than changing signs in code.

## Raspberry Pi software

```bash
sudo apt update
sudo apt install -y git i2c-tools libgl1 libglib2.0-0 libportaudio2
sudo raspi-config   # enable I2C; camera is enabled by default on current Pi OS
libcamera-hello --list-cameras
sudo i2cdetect -y 1
```

Then:

```bash
conda create -n avfm python=3.11 -c conda-forge -y
conda run -n avfm python -m pip install -e ".[dev,mediapipe,rpi]"
conda run -n avfm avfm models download --all
conda run -n avfm avfm doctor --probe-camera --probe-actuator
```

`picamera2` is normally installed with `sudo apt install -y python3-picamera2`. If you use a
different Python environment, ensure the `picamera2` Python bindings and `libcamera` are visible
to that environment.

## Camera only, no servos (passive)

Use `--servo none` and `configs/rpi_passive.toml`. The camera stays fixed, the face is tracked
in-frame, desired pan/tilt angles are logged, and fatigue monitoring works normally. No physical
search is performed.

## Safety

- Power servos from an external supply with sufficient current; brownouts can reset the Pi.
- Test one axis at a time with small angles before enabling the PID loop.
- Keep hands clear of the gimbal; use an emergency stop / unplug the servo supply.
- Do not use this project as a certified safety device.

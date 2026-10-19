"""How to plug in a custom servo/actuator.

This is a stub; it does not import pyserial. A real serial backend would send
angle commands to an ESP32/STM32 and read acknowledgements. Set can_move=True
only if the actuator actually moves the camera.
"""

from __future__ import annotations

from avfm.actuation.base import Servo


class SerialServoStub(Servo):
    name = "serial-stub"
    can_move = True
    physical = True

    def __init__(self, port: str = "COM3") -> None:
        self.port = port
        self._angle = 90.0

    def set_angle(self, angle: float) -> None:
        self._angle = angle
        # A real implementation would write a line such as:
        #   self._serial.write(f"PAN {angle:.2f}\n".encode())
        # and optionally wait for an ACK.

    def get_angle(self) -> float:
        return self._angle

    def close(self) -> None:
        return None

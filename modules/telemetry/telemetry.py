"""
Telemetry gathering logic.
"""

import time

from pymavlink import mavutil

from ..common.modules.logger import logger


class TelemetryData:  # pylint: disable=too-many-instance-attributes
    """
    Python struct to represent Telemtry Data. Contains the most recent attitude and position reading.
    """

    def __init__(
        self,
        time_since_boot: int | None = None,  # ms
        x: float | None = None,  # m
        y: float | None = None,  # m
        z: float | None = None,  # m
        x_velocity: float | None = None,  # m/s
        y_velocity: float | None = None,  # m/s
        z_velocity: float | None = None,  # m/s
        roll: float | None = None,  # rad
        pitch: float | None = None,  # rad
        yaw: float | None = None,  # rad
        roll_speed: float | None = None,  # rad/s
        pitch_speed: float | None = None,  # rad/s
        yaw_speed: float | None = None,  # rad/s
    ) -> None:
        self.time_since_boot = time_since_boot
        self.x = x
        self.y = y
        self.z = z
        self.x_velocity = x_velocity
        self.y_velocity = y_velocity
        self.z_velocity = z_velocity
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.roll_speed = roll_speed
        self.pitch_speed = pitch_speed
        self.yaw_speed = yaw_speed

    def __str__(self) -> str:
        return f"""{{
            time_since_boot: {self.time_since_boot},
            x: {self.x},
            y: {self.y},
            z: {self.z},
            x_velocity: {self.x_velocity},
            y_velocity: {self.y_velocity},
            z_velocity: {self.z_velocity},
            roll: {self.roll},
            pitch: {self.pitch},
            yaw: {self.yaw},
            roll_speed: {self.roll_speed},
            pitch_speed: {self.pitch_speed},
            yaw_speed: {self.yaw_speed}
        }}"""


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Telemetry:
    """
    Telemetry class to read position and attitude (orientation).
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> object:
        """
        Falliable create (instantiation) method to create a Telemetry object.
        """
        return Telemetry(cls.__private_key, connection, local_logger)  # Create a Telemetry object

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> None:
        assert key is Telemetry.__private_key, "Use create() method"

        self.connection = connection
        self.local_logger = local_logger

    def run(
        self,
        # Put your own arguments here
    ) -> TelemetryData:
        """
        Receive LOCAL_POSITION_NED and ATTITUDE messages from the drone,
        combining them together to form a single TelemetryData object.
        """
        start_time = time.time()
        local_position = None
        attitude = None
        while time.time() - start_time < 1:
            msg = self.connection.recv_match(blocking=False)
            if msg:
                self.local_logger.info(f"Received: {msg.get_type()}")
            # Read MAVLink message LOCAL_POSITION_NED (32)
            if msg and msg.get_type() == "LOCAL_POSITION_NED":
                local_position = msg
            elif msg and msg.get_type() == "ATTITUDE":
                attitude = msg
            if attitude and local_position:
                max_time_since_boot = max(local_position.time_boot_ms, attitude.time_boot_ms)
                # Return the most recent of both, and use the most recent message's timestamp
                return TelemetryData(
                    max_time_since_boot,
                    local_position.x,
                    local_position.y,
                    local_position.z,
                    local_position.vx,
                    local_position.vy,
                    local_position.vz,
                    attitude.roll,
                    attitude.pitch,
                    attitude.yaw,
                    attitude.rollspeed,
                    attitude.pitchspeed,
                    attitude.yawspeed,
                )
        self.local_logger.warning("Did not receive messages, restarting...")
        return None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================

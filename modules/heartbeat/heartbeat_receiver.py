"""
Heartbeat receiving logic.
"""

from pymavlink import mavutil

from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatReceiver:
    """
    HeartbeatReceiver class to send a heartbeat
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        # args,  # Put your own arguments here
        local_logger: logger.Logger,
    ) -> object:
        """
        Falliable create (instantiation) method to create a HeartbeatReceiver object.
        """
        return HeartbeatReceiver(cls.__private_key, connection, local_logger)

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        # args,  # Put your own arguments here
        local_logger: logger.Logger,
    ) -> None:
        assert key is HeartbeatReceiver.__private_key, "Use create() method"

        # Do any intializiation here
        self.connection = connection
        self.local_logger = local_logger
        self.missed = 0
        self.state = "Disconnected"

    def run(
        self,
        # args,  # Put your own arguments here
    ) -> str:
        """
        Attempt to recieve a heartbeat message.
        If disconnected for over a threshold number of periods,
        the connection is considered disconnected.
        """
        msg = self.connection.recv_match(type="HEARTBEAT")
        if not msg:
            self.missed += 1
            self.local_logger.warning(f"Missed Heartbeat {self.missed}")
            if self.missed >= 5:
                self.state = "Disconnected"
        else:
            self.missed = 0
            self.state = "Connected"
        return self.state


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================

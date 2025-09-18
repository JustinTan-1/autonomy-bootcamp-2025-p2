"""
Heartbeat worker that sends heartbeats periodically.
"""

import os
import pathlib
import time

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from . import heartbeat_receiver
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def heartbeat_receiver_worker(
    connection: mavutil.mavfile,
    controller: worker_controller.WorkerController,  # Place your own arguments here
    output_queue: queue_proxy_wrapper.QueueProxyWrapper,
    heartbeat_time: int,
    # Add other necessary worker arguments here
) -> None:
    """
    Worker process.

    connection - connection to drone
    controller - worker controller
    output_queue - worker output queue
    HEATBEAT_TIME - time for a single heartbeat
    """
    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    # Instantiate logger
    worker_name = pathlib.Path(__file__).stem
    process_id = os.getpid()
    result, local_logger = logger.Logger.create(f"{worker_name}_{process_id}", True)
    if not result:
        print("ERROR: Worker failed to create logger")
        return

    # Get Pylance to stop complaining
    assert local_logger is not None

    local_logger.info("Logger initialized", True)

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Instantiate class object (heartbeat_receiver.HeartbeatReceiver)

    heart_beat_receiver_object = heartbeat_receiver.HeartbeatReceiver.create(
        connection, local_logger
    )
    while not controller.is_exit_requested():
        controller.check_pause()
        result = heart_beat_receiver_object.run()
        if result:
            output_queue.queue.put(result)
        time.sleep(heartbeat_time)
    # Main loop: do work.


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================

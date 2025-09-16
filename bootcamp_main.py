"""
Bootcamp F2025

Main process to setup and manage all the other working processes
"""

import multiprocessing as mp
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger
from modules.common.modules.logger import logger_main_setup
from modules.common.modules.read_yaml import read_yaml
from modules.command import command
from modules.command import command_worker
from modules.heartbeat import heartbeat_receiver_worker
from modules.heartbeat import heartbeat_sender_worker
from modules.telemetry import telemetry_worker
from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from utilities.workers import worker_manager


# MAVLink connection
CONNECTION_STRING = "tcp:localhost:12345"

# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
# Set queue max sizes (<= 0 for infinity)
QUEUE_MAX_SIZE = 0
# Set worker counts
HEARTBEAT_SENDER_WORKER_COUNT = 2
HEARTBEAT_RECEIVER_WORKER_COUNT = 2
TELEMETRY_WORKER_COUNT = 2
COMMAND_WORKER_COUNT = 2
# Any other constants
TARGET = command.Position(10, 20, 30)

# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================


def main() -> int:
    """
    Main function.
    """
    # Configuration settings
    result, config = read_yaml.open_config(logger.CONFIG_FILE_PATH)
    if not result:
        print("ERROR: Failed to load configuration file")
        return -1

    # Get Pylance to stop complaining
    assert config is not None

    # Setup main logger
    result, main_logger, _ = logger_main_setup.setup_main_logger(config)
    if not result:
        print("ERROR: Failed to create main logger")
        return -1

    # Get Pylance to stop complaining
    assert main_logger is not None

    # Create a connection to the drone. Assume that this is safe to pass around to all processes
    # In reality, this will not work, but to simplify the bootamp, preetend it is allowed
    # To test, you will run each of your workers individually to see if they work
    # (test "drones" are provided for you test your workers)
    # NOTE: If you want to have type annotations for the connection, it is of type mavutil.mavfile
    connection = mavutil.mavlink_connection(CONNECTION_STRING)
    connection.wait_heartbeat(timeout=30)  # Wait for the "drone" to connect

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Create a worker controller
    controller = worker_controller.WorkerController()
    # Create a multiprocess manager for synchronized queues
    mp_manager = mp.Manager()
    # Create queues
    heartbeat_receiver_output_queue = queue_proxy_wrapper.QueueProxyWrapper(
        mp_manager,
        QUEUE_MAX_SIZE,
    )
    command_input_queue = queue_proxy_wrapper.QueueProxyWrapper(
        mp_manager,
        QUEUE_MAX_SIZE,
    )
    command_output_queue = queue_proxy_wrapper.QueueProxyWrapper(
        mp_manager,
        QUEUE_MAX_SIZE,
    )

    # Create worker properties for each worker type (what inputs it takes, how many workers)
    # Heartbeat sender
    result, heartbeat_sender_worker_properties = worker_manager.WorkerProperties.create(
        count=HEARTBEAT_SENDER_WORKER_COUNT,  # How many workers
        target=heartbeat_sender_worker.heartbeat_sender_worker,  # What's the function that this worker runs
        work_arguments=(  # The function's arguments excluding input/output queues and controller
            connection,
        ),
        input_queues=[],  # Note that input/output queues must be in the proper order
        output_queues=[],
        controller=controller,  # Worker controller
        local_logger=main_logger,  # Main logger to log any failures during worker creation
    )
    if not result:
        print("Failed to create arguments for heartbeat_sender")
        return -1
    assert heartbeat_sender_worker_properties is not None
    # Heartbeat receiver
    result, heartbeat_receiver_worker_properties = worker_manager.WorkerProperties.create(
        count=HEARTBEAT_RECEIVER_WORKER_COUNT,  # How many workers
        target=heartbeat_receiver_worker.heartbeat_receiver_worker,  # What's the function that this worker runs
        work_arguments=(  # The function's arguments excluding input/output queues and controller
            connection,
            1,
        ),
        input_queues=[],  # Note that input/output queues must be in the proper order
        output_queues=[heartbeat_receiver_output_queue],
        controller=controller,  # Worker controller
        local_logger=main_logger,  # Main logger to log any failures during worker creation
    )
    if not result:
        print("Failed to create arguments for heartbeat_receiver")
        return -1
    assert heartbeat_receiver_worker_properties is not None
    # Telemetry
    result, telemetry_worker_properties = worker_manager.WorkerProperties.create(
        count=TELEMETRY_WORKER_COUNT,  # How many workers
        target=telemetry_worker.telemetry_worker,  # What's the function that this worker runs
        work_arguments=(  # The function's arguments excluding input/output queues and controller
            connection,
        ),
        input_queues=[],  # Note that input/output queues must be in the proper order
        output_queues=[command_input_queue],
        controller=controller,  # Worker controller
        local_logger=main_logger,  # Main logger to log any failures during worker creation
    )
    if not result:
        print("Failed to create arguments for Telemetry")
        return -1
    assert telemetry_worker_properties is not None
    # Command
    result, command_worker_properties = worker_manager.WorkerProperties.create(
        count=COMMAND_WORKER_COUNT,  # How many workers
        target=command_worker.command_worker,  # What's the function that this worker runs
        work_arguments=(  # The function's arguments excluding input/output queues and controller
            connection,
            TARGET,
        ),
        input_queues=[
            command_input_queue
        ],  # Note that input/output queues must be in the proper order
        output_queues=[command_output_queue],
        controller=controller,  # Worker controller
        local_logger=main_logger,  # Main logger to log any failures during worker creation
    )
    if not result:
        print("Failed to create arguments for Command")
        return -1
    assert command_worker_properties is not None
    # Create the workers (processes) and obtain their managers
    worker_managers: list[worker_manager.WorkerManager] = []
    result, heartbeat_sender_manager = worker_manager.WorkerManager.create(
        worker_properties=heartbeat_sender_worker_properties,
        local_logger=main_logger,
    )
    if not result:
        print("Failed to create manager for heartbeat_sender")
        return -1
    assert heartbeat_sender_manager is not None

    result, heartbeat_receiver_manager = worker_manager.WorkerManager.create(
        worker_properties=heartbeat_receiver_worker_properties,
        local_logger=main_logger,
    )
    if not result:
        print("Failed to create manager for heartbeat_receiver")
        return -1
    assert heartbeat_receiver_manager is not None

    result, telemetry_manager = worker_manager.WorkerManager.create(
        worker_properties=telemetry_worker_properties,
        local_logger=main_logger,
    )
    if not result:
        print("Failed to create manager for telemetry")
        return -1
    assert telemetry_manager is not None

    result, command_manager = worker_manager.WorkerManager.create(
        worker_properties=command_worker_properties,
        local_logger=main_logger,
    )
    if not result:
        print("Failed to create manager for command")
        return -1
    assert command_manager is not None
    worker_managers.append(heartbeat_receiver_manager)
    worker_managers.append(heartbeat_sender_manager)
    worker_managers.append(telemetry_manager)
    worker_managers.append(command_manager)
    # Start worker processes
    for manager in worker_managers:
        manager.start_workers()
    main_logger.info("Started")

    # Main's work: read from all queues that output to main, and log any commands that we make
    # Continue running for 100 seconds or until the drone disconnects
    output_queues = [heartbeat_receiver_output_queue, command_output_queue]
    disconnect_time = time.time() + 100
    while time.time() < disconnect_time and connection:
        for item in output_queues:
            if not item.queue.empty():
                msg = item.queue.get()
                main_logger.info(msg)
    # Stop the processes
    controller.request_exit()
    main_logger.info("Requested exit")

    # Fill and drain queues from END TO START
    heartbeat_receiver_output_queue.fill_and_drain_queue()
    command_input_queue.fill_and_drain_queue()
    command_output_queue.fill_and_drain_queue()

    main_logger.info("Queues cleared")

    # Clean up worker processes
    for manager in worker_managers:
        manager.join_workers()

    main_logger.info("Stopped")

    # We can reset controller in case we want to reuse it
    # Alternatively, create a new WorkerController instance
    controller.clear_exit()
    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Failed with return code {result_main}")
    else:
        print("Success!")

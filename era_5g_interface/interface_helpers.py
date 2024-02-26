import json
import logging
import os
import sys
from threading import Event, Thread
from typing import Callable, Dict, List

import numpy as np
import psutil
import requests

logger = logging.getLogger(__name__)

# Middleware address.
MIDDLEWARE_ADDRESS = str(os.getenv("MIDDLEWARE_ADDRESS", "http://localhost"))
MIDDLEWARE_ADDRESS = MIDDLEWARE_ADDRESS if MIDDLEWARE_ADDRESS.startswith("http") else ("http://" + MIDDLEWARE_ADDRESS)

MIDDLEWARE_REPORT_INTERVAL = float(os.getenv("MIDDLEWARE_REPORT_INTERVAL", 1))

# Event name used for communication between clients and heartbeat module.
HEARTBEAT_CLIENT_EVENT = "heartbeat_client_event"


class LatencyMeasurements:
    """Class for holding data about processing times (latency)."""

    def __init__(self, num_latencies_to_keep: int = 10) -> None:
        self.num_latencies_to_keep = num_latencies_to_keep
        self.processing_latencies = np.zeros(num_latencies_to_keep)

    def store_latency(self, latency: float) -> None:
        """Store latency into "circular" list.

        Args:
            latency (float): Last latency.
        """

        # Remove the oldest entry and add the new one
        # Using strategy "Copy one before and substitute at the end" (fastest)
        self.processing_latencies[0:-1] = self.processing_latencies[1:]
        self.processing_latencies[-1] = latency

    def get_latencies(self) -> List[float]:
        """Get latencies.

        Returns:
            Latencies in list
        """
        latencies: list = self.processing_latencies.tolist()
        return latencies

    def get_avg_latency(self) -> float:
        """Get average latency.

        Returns:
            Average latency.
        """

        return float(np.mean(self.processing_latencies))


class RepeatedTimer(Thread):
    """Repeated interval timer of callback function in Thread."""

    def __init__(self, interval: float, callback: Callable):
        """Constructor.

        Args:
            interval (float): Interval in seconds.
            callback (Callable): Function to be called repeatedly.
        """

        super().__init__(daemon=True)
        self._stop_event = Event()
        self._callback = callback
        self._interval = interval

    def stop(self) -> None:
        """Set stop event to stop FCW worker."""

        self._stop_event.set()

    def run(self):
        """Periodically calls callback function."""

        self._stop_event = Event()
        while not self._stop_event.wait(self._interval):
            self._callback()


class HeartbeatSender:
    """Heartbeat to Middleware sender."""

    def __init__(
        self, status_address: str, heartbeat_data_callback: Callable[[], Dict], repeat_on_error: bool = False
    ) -> None:
        """Constructor, create RepeatedTimer and requests.Session.

        Args:
            status_address (str): Status reporting address.
            heartbeat_data_callback (Callable[[], Dict]): Callback that generates JSON data for heartbeat reporting.
            repeat_on_error (bool): If set, repeat requests further. Defaults to False.
        """

        self.session: requests.Session = requests.Session()
        self.session.headers.update({"Content-type": "application/json"})
        self.connection_error = False
        self.heartbeat_data_callback = heartbeat_data_callback
        self.status_address = status_address
        self.repeat_on_error = repeat_on_error
        self.heartbeat_timer = RepeatedTimer(MIDDLEWARE_REPORT_INTERVAL, self._send_heartbeat_request)
        self.heartbeat_timer.start()

    def _send_heartbeat_request(self) -> None:
        """Send heartbeat request to Middleware."""

        data = self.heartbeat_data_callback()
        if not self.connection_error or self.repeat_on_error:
            logger.debug(f"Sending heartbeat to middleware {self.status_address}: \n{data}")
            try:
                response = self.session.post(self.status_address, json=data, timeout=(1.5, 1.5))
                if response.ok:
                    logger.debug(f"Middleware heartbeat response: \n{self._decode_response(response)}")
                else:
                    logger.warning(
                        f"Middleware heartbeat response: {response}, middleware address: {self.status_address}\n"
                        f"{self._decode_response(response)}"
                    )
                    # self.connection_error = True
            except requests.RequestException as e:
                logger.warning(f"Failed to connect to the middleware address: {self.status_address}, {repr(e)}")
                self.connection_error = True

    def _decode_response(self, response):
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.warning(f"Cannot decode JSON: {repr(e)}, response: {response.text}")
            return {}


if __name__ == "__main__":
    # Heartbeat sending test.
    logging.basicConfig(
        stream=sys.stdout, level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger(__name__)

    def generate_application_heartbeat_data() -> Dict:
        data = {
            "id": "a04dee9a-c303-43b7-8f1b-6c986ad21a99",
            "name": "test",
            "currentRobotsCount": 3,
            "optimalLimit": 5,
            "hardLimit": 10,
        }
        return data

    def generate_robot_heartbeat_data() -> Dict:
        battery_status = psutil.sensors_battery()
        data = {
            "id": "300c719a-1c06-4500-a13a-c2e20592b273",
            "actionSequenceId": None,
            "currentlyExecutedActionIndex": None,
            "batteryLevel": battery_status.percent if battery_status else 100,  # Robot battery level.
            "cpuUtilisation": psutil.cpu_percent(percpu=False),  # Robot CPU utilization.
            "ramUtilisation": psutil.virtual_memory().percent,  # Robot RAM utilization.
        }
        return data

    heartbeat_sender = HeartbeatSender(MIDDLEWARE_ADDRESS + "/status/netapp", generate_application_heartbeat_data)
    heartbeat_sender._send_heartbeat_request()
    del heartbeat_sender
    heartbeat_sender = HeartbeatSender(MIDDLEWARE_ADDRESS + "/status/robot", generate_robot_heartbeat_data)
    heartbeat_sender._send_heartbeat_request()
    del heartbeat_sender

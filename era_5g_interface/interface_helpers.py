import logging
import math
import os
from typing import Any

import numpy as np
import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)

NETAPP_ID = str(os.getenv("NETAPP_ID", "00000000-0000-0000-0000-000000000000"))
NETAPP_ID_ROS = NETAPP_ID.replace("-", "_")
MIDDLEWARE_ADDRESS = str(os.getenv("MIDDLEWARE_ADDRESS", "http://localhost"))
MIDDLEWARE_REPORT_INTERVAL = float(os.getenv("MIDDLEWARE_REPORT_INTERVAL", 1))
MAX_LATENCY = float(os.getenv("NETAPP_MAX_LATENCY", 100))


class LatencyMeasurements:
    """Class for holding data about processing times (latency)"""

    def __init__(self, num_latencies_to_keep: int = 10) -> None:
        self.num_latencies_to_keep = num_latencies_to_keep
        self.processing_latencies = np.zeros(num_latencies_to_keep)

    def store_latency(self, latency: float) -> None:
        # Remove the oldest entry and add the new one
        # Using strategy "Copy one before and substitute at the end" (fastest)
        self.processing_latencies[0:-1] = self.processing_latencies[1:]
        self.processing_latencies[-1] = latency

    def get_latencies(self) -> Any:
        return self.processing_latencies.tolist()

    def get_avg_latency(self) -> float:
        return float(np.mean(self.processing_latencies))


class HeartBeatSender:
    def __init__(self) -> None:
        self.retries = Retry(total=0, read=0, connect=0, backoff_factor=0, status_forcelist=[429, 500, 502, 503, 504])

        self.session: requests.Session = requests.Session()
        self.adapter: HTTPAdapter = HTTPAdapter(max_retries=self.retries)
        self.session.mount(MIDDLEWARE_ADDRESS, self.adapter)
        self.connection_error = False

    def send_middleware_heart_beat_request(self, headers: dict, json: dict) -> None:
        if not self.connection_error:
            logger.info(f"Sending heart beat to middleware: {json}")
            try:
                response = self.session.post(MIDDLEWARE_ADDRESS, headers=headers, json=json, timeout=(0.2, 0.2))
                logger.info(f"Middleware heart_beat response: {response.text}")
            except requests.RequestException as e:
                logger.warning(f"Failed to connect to the middleware address: {MIDDLEWARE_ADDRESS}, {repr(e)}")
                self.connection_error = True

    def send_middleware_heart_beat(
        self, avg_latency: float, queue_size: int, queue_occupancy: float, current_robot_count: int
    ) -> None:
        # Latency can change over time, so reporting just the simple que occupancy can be misleading.
        # Instead, it is better to report occupancy in terms of:
        #  'total time estimated to be needed to process everything in the queue' / 'required max latency'
        processing_time_occupancy = queue_size * avg_latency / MAX_LATENCY

        if queue_size == 0:
            # If the queue is empty then no estimate can be made about robot count limit,
            # but most likely at least one more robot can be added.
            hard_robot_count_limit = current_robot_count + 1
            optimal_robot_count_limit = current_robot_count + 1
        elif avg_latency == 0:
            # If there are no latency measurements, the maximum number of robots cannot be estimated
            # using processing_time_occupancy, but we can still try to use queue_occupancy.
            hard_robot_count_limit = math.floor(current_robot_count / queue_occupancy)
            optimal_robot_count_limit = math.floor(hard_robot_count_limit * 0.8)
        else:
            hard_robot_count_limit = math.floor(current_robot_count / processing_time_occupancy)
            optimal_robot_count_limit = math.floor(hard_robot_count_limit * 0.8)

        data = {
            "Id": NETAPP_ID,
            "CurrentRobotsCount": current_robot_count,
            "OptimalLimit": optimal_robot_count_limit,
            "HardLimit": hard_robot_count_limit,
        }
        headers = {"Content-type": "application/json"}
        self.send_middleware_heart_beat_request(headers=headers, json=data)
        # TODO: only for testing purpose
        # logger.info(f"Heart beat published to middleware: {data}")

import csv
import logging
import time
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class Measuring:
    """Measuring class is used to define and measure and log timestamps or custom data to csv file."""

    def __init__(
        self,
        measuring_items: Dict[str, Any],
        enabled: bool = False,
        filename_prefix: str = "measuring",
    ):
        """Constructor."""

        self._enabled = enabled
        if self._enabled:
            self._measuring: Dict[int, Any] = {}
            self._measuring_file = open(
                "{}-{}.csv".format(filename_prefix, datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]),
                "w",
                newline="\n",
            )
            self._csv_writer = csv.writer(self._measuring_file)
            self._measuring_items = measuring_items
            if "key_timestamp" not in self._measuring_items:
                self._measuring_items["key_timestamp"] = 0
            self._csv_writer.writerow(self._measuring_items.keys())
            self._measuring_file.flush()

    def log_measuring(self, key_timestamp: int, key: str, value: Any) -> None:
        if self._enabled:
            if key_timestamp not in self._measuring:
                self._measuring[key_timestamp] = self._measuring_items.copy()
                self._measuring[key_timestamp]["key_timestamp"] = key_timestamp
            self._measuring[key_timestamp][key] = value

    def log_timestamp(self, key_timestamp: int, key: str) -> None:
        self.log_measuring(key_timestamp, key, time.perf_counter_ns())

    def store_measuring(self, key_timestamp: int) -> None:
        if self._enabled:
            self._csv_writer.writerow(self._measuring[key_timestamp].values())
            self._measuring_file.flush()

from abc import ABC, abstractmethod
from typing import Any, Optional

from era_5g_interface.dataclasses.control_command import ControlCommand


class TaskHandlerInitializationFailed(Exception):
    pass


class TaskHandler(ABC):
    """Abstract class.

    Task handler which takes care of receiving data from the NetApp
    client and passing them to the NetApp worker.
    """

    def __init__(self, sid: str, decoder=None) -> None:
        self.sid = sid
        self.websocket_id: Optional[str] = None
        self.frame_id = 0
        self.decoder = decoder
        self.last_timestamp = 0

    @abstractmethod
    def store_data(self, metadata: dict, data: Any) -> None:
        """This method is intended to pass the image to the worker (using
        internal queues, message broker or anything else).

        Args:
            metadata (dict): Arbitrary dictionary with metadata related to the image.
                The format is NetApp-specific.
            image (_type_): The image to be processed.
        """

        pass

    @abstractmethod
    def store_control_data(self, data: ControlCommand) -> None:
        """This method is intended to pass control commands to the worker.

        Args:
            data (ControlCommand): ControlCommand with control data.
        """

        pass

    @abstractmethod
    def clear_storage(self) -> None:
        """Clear storage used for communication with worker."""

        pass

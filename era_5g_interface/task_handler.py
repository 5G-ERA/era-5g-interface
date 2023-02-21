from abc import ABC, abstractmethod
from threading import Event, Thread
from typing import Optional


class TaskHandlerInitializationFailed(Exception):
    pass


class TaskHandler(Thread, ABC):
    """Abstract class.

    Thread-based task handler which takes care of receiving data from
    the NetApp client and passing them to the NetApp worker.
    """

    def __init__(self, sid: str, **kw) -> None:
        super().__init__(**kw)
        self.stop_event = Event()
        self.sid = sid
        self.websocket_id: Optional[str] = None

    def stop(self):
        self.stop_event.set()

    @abstractmethod
    def run(self) -> None:
        """This method is run once the thread is started and could be used for
        periodical retrieval of images."""

        pass

    @abstractmethod
    def store_image(self, metadata: dict, image: bytes) -> None:
        """This method is intended to pass the image to the worker (using
        internal queues, message broker or anything else).

        Args:
            metadata (dict): Arbitrary dictionary with metadata related to the image.
                The format is NetApp-specific.
            image (_type_): The image to be processed.
        """

        pass

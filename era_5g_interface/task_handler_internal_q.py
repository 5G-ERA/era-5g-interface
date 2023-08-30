import logging
from enum import IntEnum
from queue import Empty, Full, Queue
from threading import Lock
from typing import Any, Optional

from era_5g_interface.dataclasses.control_command import ControlCommand
from era_5g_interface.task_handler import TaskHandler

logger: logging.Logger = logging.getLogger(__name__)


class QueueFullAction(IntEnum):
    DISCARD_OLDEST = 1
    DISCARD_NEW = 2
    RAISE = 3


class QueueDiscardError(Exception):
    """Exception which is raised when a problem occurs during discarding of old
    data when internal queue is full."""

    pass


class TaskHandlerInternalQ(TaskHandler):
    """Task handler which takes care of passing the data to the python internal
    queue for future processing.

    It could either be inherited to implement the _run method and read
    the data from any source or used directly and call the store_data
    method externally.
    """

    def __init__(
        self,
        sid: str,
        data_queue: Queue,
        if_queue_full: QueueFullAction = QueueFullAction.DISCARD_OLDEST,
        queue_put_lock: Optional[Lock] = None,
        **kw,
    ) -> None:
        """
        Constructor
        Args:
            sid (str): The session id obtained from NetApp client. It is used
                to match the results with the data sender.
            data_queue (Queue): The queue where the data and metadata should
                be passed to.
            if_queue_full (QueueFullAction, Optional):
                This parameter defines what should happen in case the internal
                queue is full and new data is to be added. Possible actions
                are defined by QueueFullAction Enum: DISCARD_OLDEST,
                DISCARD_NEW and RAISE.
                Default is DISCARD_OLDEST, which removes the oldest item
                from the queue to make up space for the new one. Option
                DISCARD_NEW throws away the newly provided data and keeps
                the queue intact. Choosing RAISE results in raising
                RuntimeError exception.
                Note that even DISCARD_OLDEST can result in discarding the
                new data - this happens in case the oldest data is a Control
                Command. Note also that, since Control Commands are considered
                more important than regular data, attempting to discard
                new Control Commad raises an exception, even in case
                the value is set to DISCARD_NEW.
            queue_put_lock (Lock, Optional):
                Lock for preventing multiple task handlers (or calls to
                store_data from multiple threads) from adding new data during
                the possible discarding of old data when queue is full. Default
                is None (the lock will be created internally.)
        """

        super().__init__(sid=sid, **kw)
        self._q: Queue = data_queue
        assert isinstance(if_queue_full, QueueFullAction)
        self.if_queue_full = if_queue_full
        if queue_put_lock is not None:
            self._q_put_lock = queue_put_lock
        else:
            self._q_put_lock = Lock()

    def data_queue_size(self) -> int:
        return self._q.qsize()

    def data_queue_occupancy(self) -> float:
        return self._q.qsize() / self._q.maxsize

    def store_data(self, metadata: dict, data: Any) -> None:
        """Method which will store the data (e.g. an image) to the queue for
        processing.

        Args:
            metadata (dict): Arbitrary dictionary with metadata related to the data.
                The format is NetApp-specific.
            data (Any): The data to be processed.

        Raises:
            QueueDiscardError: Raised when a problem occurs during discarding
                of old data when internal queue is full.
        """

        # make sure multiple calls of store_data do not interfere with each other
        with self._q_put_lock:
            self.frame_id += 1
            # logger.info(f"TaskHandlerInternalQ received frame id: {self.frame_id} with timestamp: {metadata['timestamp']}")

            try:
                self._q.put((metadata, data), block=False)
            except Full:
                if self.if_queue_full == QueueFullAction.DISCARD_NEW:
                    pass  # do nothing (discard the new data)
                elif self.if_queue_full == QueueFullAction.DISCARD_OLDEST:
                    # remove the oldest data from queue to make up space for the new one,
                    # but make sure not to discard control commands
                    space_available = False
                    with self._q.mutex:  # acquire the queue lock to prevent it from mutating during the removal
                        if isinstance(self._q.queue[0], ControlCommand):
                            logger.warning(
                                "Discarding new data instead of the old one to prevent losing a control command in queue."
                            )
                            # this situation could also raise an exception, if desired
                        else:
                            self._q._get()  # remove the old data from queue
                            space_available = True

                    if space_available:
                        self._q.put((metadata, data), block=False)
                else:
                    raise QueueDiscardError("Internal queue is full and no data was allowed to be discarded.")

    def store_control_data(self, data: ControlCommand) -> None:
        """Pass control commands to the worker using internal queue.

        Args:
            data (ControlCommand): ControlCommand with control data.

        Raises:
            QueueDiscardError: Raised when a problem occurs during discarding
                of old data when internal queue is full.
        """

        with self._q_put_lock:
            try:
                self._q.put(data, block=False)
            except Full:
                if self.if_queue_full == QueueFullAction.DISCARD_OLDEST:
                    with self._q.mutex:
                        if isinstance(self._q.queue[0], ControlCommand):
                            raise QueueDiscardError(
                                "Internal queue is full, and the new Control Command would discard a previous one."
                            )
                        else:
                            self._q._get()  # remove the old data from queue

                    self._q.put(data, block=False)
                else:
                    raise QueueDiscardError("Internal queue is full, Control Command cannot be processed.")

    def clear_storage(self) -> None:
        """Clear all items from internal queue."""

        while not self._q.empty():
            try:
                self._q.get(block=False)
            except Empty:
                break
            self._q.task_done()

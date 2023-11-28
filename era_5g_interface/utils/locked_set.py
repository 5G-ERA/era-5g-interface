from threading import Lock
from typing import Any, Iterator


class LockedSet(set):
    """A set which can be safely iterated and modified from different threads."""

    def __init__(self, *args, **kwargs):
        self._lock = Lock()
        super(LockedSet, self).__init__(*args, **kwargs)

    def add(self, elem: Any):
        with self._lock:
            super(LockedSet, self).add(elem)

    def remove(self, elem: Any):
        with self._lock:
            super(LockedSet, self).remove(elem)

    def discard(self, elem: Any) -> None:
        with self._lock:
            return super(LockedSet, self).remove(elem)

    def __contains__(self, elem: Any):
        with self._lock:
            super(LockedSet, self).__contains__(elem)

    def locked_iter(self, it: Iterator) -> Iterator:
        it = iter(it)

        while True:
            try:
                with self._lock:
                    value = next(it)
            except StopIteration:
                return
            yield value

    def __iter__(self) -> Iterator:
        return self.locked_iter(super().__iter__())

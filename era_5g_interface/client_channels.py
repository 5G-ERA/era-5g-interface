import logging
from typing import Any, Dict, Optional

import socketio

from era_5g_interface.channels import DATA_ERROR_EVENT, DATA_NAMESPACE, CallbackInfoClient, Channels, ChannelType
from era_5g_interface.exceptions import BackPressureException

logger = logging.getLogger(__name__)


class ClientChannels(Channels):
    """Channels class is used to define channel data callbacks and contains send functions.

    It handles image frames JPEG and H.264 encoding/decoding.
    """

    _callbacks_info: Dict[str, CallbackInfoClient]

    def __init__(self, sio: socketio.Client, callbacks_info: Dict[str, CallbackInfoClient], **kwargs):
        """Constructor.

        Args:
            sio (socketio.Client): Socketio Client object.
            callbacks_info (Dict[str, CallbackInfoClient]): Callbacks Info dictionary, key is custom event name.
            **kw: Channels arguments.
        """

        super().__init__(sio, callbacks_info, **kwargs)

        self._sio.on(DATA_ERROR_EVENT, lambda data: self.data_error_callback(data), namespace=DATA_NAMESPACE)

        for event, callback_info in self._callbacks_info.items():
            logger.info(f"Creating client channels callback, type: {callback_info.type}, event: '{event}'")
            if callback_info.type is ChannelType.JSON:
                self._sio.on(
                    event,
                    lambda data, local_event=event: self.json_callback(data, local_event),
                    namespace=DATA_NAMESPACE,
                )
            elif callback_info.type in (ChannelType.JPEG, ChannelType.H264):
                self._sio.on(
                    event,
                    lambda data, local_event=event: self.image_callback(data, local_event),
                    namespace=DATA_NAMESPACE,
                )
            else:
                raise ValueError(f"Unknown channel type: {callback_info.type}")

    def _apply_back_pressure(self) -> None:
        """Apply back pressure."""

        if self._back_pressure_size is not None:
            if self._sio.eio.queue.qsize() > self._back_pressure_size:
                raise BackPressureException()

    def send_data(
        self, data: Dict[str, Any], event: str, sid: Optional[str] = None, can_be_dropped: bool = True
    ) -> None:
        """Send general JSON data via DATA_NAMESPACE.

        NOTE: DATA_NAMESPACE is assumed to be a connected namespace.

        Args:
            data (Dict[str, Any]): JSON data.
            event (str): Event name.
            sid (str, optional): Namespace sid - mandatory when sending from the server side to the client.
            can_be_dropped (bool): If data can be lost due to back pressure.
        """

        if can_be_dropped:
            self._apply_back_pressure()
        super().send_data(data, event, sid=sid)

    def json_callback(self, data: Dict[str, Any], event: str) -> None:
        """Allows to receive general json data on DATA_NAMESPACE.

        Args:
            data (Dict[str, Any]): JSON data.
            event (str): Event name.
        """

        self._callbacks_info[event].callback(data)

    def image_callback(self, data: Dict[str, Any], event: str) -> None:
        """Allows to receive JPEG or H.264 encoded image on DATA_NAMESPACE.

        Args:
            data (Dict[str, Any]): Received dictionary with frame data.
            event (str): Event name.
        """

        decoded_data = super().image_decode(data, event)
        if decoded_data:
            self._callbacks_info[event].callback(decoded_data)

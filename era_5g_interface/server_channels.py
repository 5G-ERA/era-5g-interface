import logging
from typing import Any, Dict, Optional

import socketio

from era_5g_interface.channels import DATA_ERROR_EVENT, DATA_NAMESPACE, CallbackInfoServer, Channels, ChannelType
from era_5g_interface.exceptions import BackPressureException

logger = logging.getLogger(__name__)


class ServerChannels(Channels):
    """Channels class is used to define channel data callbacks and contains send functions.

    It handles image frames JPEG and H.264 encoding/decoding. Data is sent via the DATA_NAMESPACE.
    """

    _callbacks_info: Dict[str, CallbackInfoServer]

    def __init__(self, sio: socketio.Server, callbacks_info: Dict[str, CallbackInfoServer], **kwargs):
        """Constructor.

        Args:
            sio (socketio.Server): Socketio Server object.
            callbacks_info (Dict[str, CallbackInfoServer]): Callbacks Info dictionary, key is custom event name.
            **kw: Channels arguments.
        """

        super().__init__(sio, callbacks_info, **kwargs)

        self._sio.on(DATA_ERROR_EVENT, lambda sid, data: self.data_error_callback(data, sid), namespace=DATA_NAMESPACE)

        for event, callback_info in self._callbacks_info.items():
            logger.info(f"Creating server channels callback, type: {callback_info.type}, event: '{event}'")
            if callback_info.type is ChannelType.JSON:
                self._sio.on(
                    event,
                    lambda sid, data, local_event=event: self.json_callback(data, local_event, sid),
                    namespace=DATA_NAMESPACE,
                )
            elif callback_info.type in (ChannelType.JPEG, ChannelType.H264):
                self._sio.on(
                    event,
                    lambda sid, data, local_event=event: self.image_callback(data, local_event, sid),
                    namespace=DATA_NAMESPACE,
                )
            else:
                raise ValueError(f"Unknown channel type: {callback_info.type}")

    def _apply_back_pressure(self, sid: Optional[str] = None) -> None:
        """Apply back pressure.

        Args:
            sid (str, optional): Namespace sid - mandatory for using on the server side.
        """

        if self._back_pressure_size is not None:
            eio_sid = self.get_client_eio_sid(str(sid), DATA_NAMESPACE)
            if self._sio.eio.sockets[eio_sid].queue.qsize() > self._back_pressure_size:
                raise BackPressureException()

    def send_data(
        self, data: Dict[str, Any], event: str, sid: Optional[str] = None, can_be_dropped: bool = False
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
            self._apply_back_pressure(sid=sid)
        super().send_data(data, event, sid=sid)

    def json_callback(self, data: Dict[str, Any], event: str, sid: str) -> None:
        """Allows to receive general json data on DATA_NAMESPACE.

        Args:
            data (Dict[str, Any]): JSON data.
            event (str): Event name.
            sid (str, optional): Namespace sid - only on the server side.
        """

        self._callbacks_info[event].callback(sid, data)

    def image_callback(self, data: Dict[str, Any], event: str, sid: str) -> None:
        """Allows to receive JPEG or H.264 encoded image on DATA_NAMESPACE.

        Args:
            data (Dict[str, Any]): Received dictionary with frame data.
            event (str): Event name.
            sid (str, optional): Namespace sid - only on the server side.
        """

        decoded_data = super().image_decode(data, event, sid)
        if decoded_data:
            self._callbacks_info[event].callback(sid, decoded_data)

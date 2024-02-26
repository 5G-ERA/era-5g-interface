import logging
import time
from typing import Any, Dict

import socketio

from era_5g_interface.channels import DATA_ERROR_EVENT, DATA_NAMESPACE, CallbackInfoServer, Channels, ChannelType

logger = logging.getLogger(__name__)


class ServerChannels(Channels):
    """Channels class is used to define channel data callbacks and contains send functions.

    It handles image frames JPEG, H.264 and HEVC, and JSON LZ4 encoding/decoding. Data is sent via the DATA_NAMESPACE.
    """

    _callbacks_info: Dict[str, CallbackInfoServer]

    def __init__(
        self,
        sio: socketio.Server,
        callbacks_info: Dict[str, CallbackInfoServer],
        **kwargs,
    ):
        """Constructor.

        Args:
            sio (socketio.Server): Socketio Server object.
            callbacks_info (Dict[str, CallbackInfoServer]): Callbacks Info dictionary, key is custom event name.
            disconnect_callback (Callable, optional): Triggered before _shutdown on unhandled exception.
            back_pressure_size (int, optional): Back pressure size - max size of eio.queue.qsize().
            recreate_coder_attempts_count (int): How many times try to recreate the frame encoder/decoder.
            stats (bool): Store output data sizes.
            extended_measuring (bool): Enable logging of measuring.
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
            elif callback_info.type is ChannelType.JSON_LZ4:
                self._sio.on(
                    event,
                    lambda sid, data, local_event=event: self.json_lz4_callback(data, local_event, sid),
                    namespace=DATA_NAMESPACE,
                )
            elif callback_info.type in (ChannelType.JPEG, ChannelType.H264, ChannelType.HEVC):
                self._sio.on(
                    event,
                    lambda sid, data, local_event=event: self.image_callback(data, local_event, sid),
                    namespace=DATA_NAMESPACE,
                )
            else:
                raise ValueError(f"Unknown channel type: {callback_info.type}")

    def json_callback(self, data: Dict[str, Any], event: str, sid: str) -> Any:
        """Allows to receive general JSON data on DATA_NAMESPACE.

        Args:
            data (Dict[str, Any]): JSON data.
            event (str): Event name.
            sid (str, optional): Namespace sid - only on the server side.
        """

        timestamp = Channels.get_timestamp_from_data(data)
        cb_info = self._callbacks_info[event]

        try:
            self._input_measuring.log_timestamp(timestamp, "before_callback_timestamp")
            return_value = cb_info.callback(sid, data)
            self._input_measuring.log_timestamp(timestamp, "after_callback_timestamp")
            self._input_measuring.log_measuring(timestamp, "eio_sid", self.get_client_eio_sid(sid, DATA_NAMESPACE))
            self._input_measuring.log_measuring(timestamp, "event", event)
            self._input_measuring.store_measuring(timestamp)
            return return_value
        except Exception:
            self._shutdown("JSON", event, sid)

    def json_lz4_callback(self, data: bytes, event: str, sid: str) -> Any:
        """Allows to receive LZ4 compressed general JSON data on DATA_NAMESPACE.

        Args:
            data (bytes): LZ4 compressed JSON data.
            event (str): Event name.
            sid (str, optional): Namespace sid - only on the server side.
        """

        before_lz4_decode_timestamp = time.perf_counter_ns()
        decoded_data = super().data_lz4_decode(data, event, sid)
        if decoded_data:
            after_lz4_decode_timestamp = time.perf_counter_ns()
            timestamp = Channels.get_timestamp_from_data(decoded_data, default=before_lz4_decode_timestamp)
            self._input_measuring.log_measuring(timestamp, "before_lz4_decode_timestamp", before_lz4_decode_timestamp)
            self._input_measuring.log_measuring(timestamp, "after_lz4_decode_timestamp", after_lz4_decode_timestamp)
            return self.json_callback(decoded_data, event, sid)

    def image_callback(self, data: Dict[str, Any], event: str, sid: str) -> Any:
        """Allows to receive JPEG or H.264 or HEVC encoded image on DATA_NAMESPACE.

        Args:
            data (Dict[str, Any]): Received dictionary with frame data.
            event (str): Event name.
            sid (str, optional): Namespace sid - only on the server side.
        """

        timestamp = Channels.get_timestamp_from_data(data)
        cb_info = self._callbacks_info[event]

        self._input_measuring.log_timestamp(timestamp, "before_decode_timestamp")
        decoded_data = super().image_decode(data, event, sid)
        self._input_measuring.log_timestamp(timestamp, "after_decode_timestamp")

        if decoded_data:
            try:
                self._input_measuring.log_timestamp(timestamp, "before_callback_timestamp")
                return_value = cb_info.callback(sid, decoded_data)
                self._input_measuring.log_timestamp(timestamp, "after_callback_timestamp")
                self._input_measuring.log_measuring(timestamp, "eio_sid", self.get_client_eio_sid(sid, DATA_NAMESPACE))
                self._input_measuring.log_measuring(timestamp, "event", event)
                self._input_measuring.store_measuring(timestamp)
                return return_value
            except Exception:
                self._shutdown("image", event, sid)

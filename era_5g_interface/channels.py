import logging
import time
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import cv2
import numpy as np
import socketio

from era_5g_interface.exceptions import UnknownChannelTypeUsed
from era_5g_interface.h264_decoder import H264Decoder, H264DecoderError
from era_5g_interface.h264_encoder import H264Encoder, H264EncoderError

logger = logging.getLogger(__name__)

# TODO: use enums?
DATA_NAMESPACE = str("/data")
DATA_ERROR_EVENT = str("data_error")

CONTROL_NAMESPACE = str("/control")
COMMAND_EVENT = str("command")
COMMAND_ERROR_EVENT = str("command_error")
COMMAND_RESULT_EVENT = str("command_result")


class ChannelType(Enum):
    """Channel type dataclass."""

    JSON = 1
    JPEG = 2
    H264 = 3


@dataclass
class CallbackInfoClient:
    """Callback info dataclass used on client side."""

    type: ChannelType  # Channel type.
    callback: Callable[[Dict], None]  # Custom callback with dict.
    error_event: str = DATA_ERROR_EVENT  # Custom error event name.


@dataclass
class CallbackInfoServer:
    """Callback info dataclass used on server side - callback has namespace sid parameter."""

    type: ChannelType  # Channel type.
    callback: Callable[[str, Dict], None]  # Custom callback with sid and dict.
    error_event: str = DATA_ERROR_EVENT  # Custom error event name.


class Channels(ABC):
    """Channels class is used to define channel data callbacks and contains send functions.

    It handles image frames JPEG and H.264 encoding/decoding. Data is sent via the DATA_NAMESPACE. The class cannot be
    used alone. The ServerChannels and ClientChannels classes create callbacks and encoders/decoders.
    """

    # This should work roughly like an abstract member.
    _callbacks_info: Union[Dict[str, CallbackInfoClient], Dict[str, CallbackInfoServer]]

    def __init__(
        self,
        sio: Union[socketio.Client, socketio.Server],
        callbacks_info: Union[Dict[str, CallbackInfoClient], Dict[str, CallbackInfoServer]],
        back_pressure_size: int = 5,
        recreate_h264_attempts_count: int = 5,
        stats: bool = False,
    ):
        """Constructor.

        Args:
            sio (Union[socketio.Client, socketio.Server]): Socketio Client or Server object.
            callbacks_info (Union[Dict[str, CallbackInfoClient], Dict[str, CallbackInfoServer]]): Callbacks Info
                dictionary, key is custom event name.
            back_pressure_size (int): Back pressure size - max size of eio.queue.qsize().
            recreate_h264_attempts_count (int): How many times try to recreate the H.264 encoder.
            stats (bool): Store output data sizes.
        """

        self._sio = sio

        if back_pressure_size is not None and back_pressure_size < 1:
            raise ValueError("Invalid value for back_pressure_size.")

        self._back_pressure_size = back_pressure_size
        self._recreate_h264_attempts_count = recreate_h264_attempts_count
        self._stats = stats
        if self._stats:
            self._sizes: List[int] = []

        self._callbacks_info = callbacks_info

        self._decoders: Dict[str, H264Decoder] = dict()
        self._encoders: Dict[str, H264Encoder] = dict()

    def send_image(
        self,
        frame: np.ndarray,
        event: str,
        channel_type: ChannelType,
        timestamp: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        sid: Optional[str] = None,
        can_be_dropped: bool = True,
        encoding_options: Optional[Dict[str, str]] = None,
    ) -> None:
        """Send general image data with JPEG or H.264 encoding via DATA_NAMESPACE.

        NOTE: DATA_NAMESPACE is assumed to be a connected namespace.

        Args:
            frame (np.ndarray): Video frame / image.
            event (str): Event name.
            channel_type (ChannelType): Encoding type - ChannelType.JPEG or ChannelType.H264.
            timestamp (int): Frame timestamp.
            metadata (Dict[str, Any], optional): Optional metadata to send.
            sid (str, optional): Namespace sid - mandatory when sending from the server side to the client.
            can_be_dropped (bool): If data can be lost due to back pressure.
            encoding_options (Dict[str, str], optional): ChannelType.H264 options, e.g. {"crf": "0", "preset":
                "ultrafast", "tune": "zerolatency", "x264-params": "keyint=5"}, default: {"preset": "ultrafast",
                "tune": "zerolatency"}.

        Parameter frame.shape should not be changed after first send_image function call.
        Parameters encoding_options and frame.shape are only used in the first send_image call to create the encoder.
        """

        if channel_type is not ChannelType.JPEG and channel_type is not ChannelType.H264:
            raise UnknownChannelTypeUsed()

        if timestamp is None:
            timestamp = time.perf_counter_ns()
        data: Dict[str, Any] = {"timestamp": timestamp}
        if metadata:
            data["metadata"] = metadata
        eio_sid = self.get_client_eio_sid(sid, DATA_NAMESPACE)

        if channel_type is ChannelType.H264:
            if eio_sid not in self._encoders:
                try:
                    logger.info(f"Creating H.264 encoder for image size {frame.shape[1]}x{frame.shape[0]}")
                    self._encoders[eio_sid] = H264Encoder(frame.shape[1], frame.shape[0], options=encoding_options)
                except Exception as e:
                    logger.error(f"Cannot create H.264 encoder: {repr(e)}")
                    raise e
        try:
            is_key_frame = True
            if channel_type is ChannelType.H264:
                frame_encoded = self._encoders[eio_sid].encode_ndarray(frame)
                # TODO: dataclass for this data
                data["h264"] = True
                data["width"] = self._encoders[eio_sid].width()
                data["height"] = self._encoders[eio_sid].height()
                is_key_frame = self._encoders[eio_sid].last_frame_is_keyframe()
            else:
                _, frame_jpeg = cv2.imencode(".jpg", frame)
                frame_encoded = frame_jpeg.tobytes()
            data["frame"] = frame_encoded
            if self._stats:
                # TODO: include all data size
                self._sizes.append(len(frame_encoded))
                logger.debug(f"Frame data size: {self._sizes[-1]}")

            self.send_data(data, event, sid, can_be_dropped and is_key_frame)
        except H264EncoderError as e:
            logger.error(f"H.264 encoder error: {e}")
            # Try to recreate encoder
            if self._encoders[eio_sid].get_init_count() < self._recreate_h264_attempts_count:
                logger.info(f"Try to recreate encoder ... attempt {self._encoders[eio_sid].get_init_count()}")
                self._encoders[eio_sid].encoder_init()
            else:
                raise e

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
        if isinstance(self._sio, socketio.Client):
            self._sio.emit(event, data, namespace=DATA_NAMESPACE)
        else:
            if sid is None:
                raise ValueError("'sid' has to be set for server.")
            self._sio.emit(event, data, namespace=DATA_NAMESPACE, to=sid)

    def get_client_eio_sid(self, sid: Optional[str] = None, namespace: Optional[str] = None) -> str:
        """Get client eio sid.

        Args:
            sid (str, optional): Namespace sid - mandatory for using on the server side.
            namespace (str, optional): Namespace - mandatory for using on the server side.

        Returns:
            Client eio sid.
        """

        if isinstance(self._sio, socketio.Client):
            return str(self._sio.sid)
        else:
            if sid is None:
                raise ValueError("'sid' has to be set for server.")
            return str(self._sio.manager.eio_sid_from_sid(sid, namespace))

    def data_error_callback(self, data: Dict[str, Any], sid: Optional[str] = None) -> None:
        """Allows to receive general error data on DATA_NAMESPACE.

        Args:
            data (Dict[str, Any]): JSON data.
            sid (str, optional): Namespace sid - only on the server side.
        """

        logger.error(f"Data error, eio_sid {self.get_client_eio_sid(sid, DATA_NAMESPACE)}, sid {sid}, data {data}")

    def image_decode(self, data: Dict[str, Any], event: str, sid: Optional[str] = None) -> Optional[Dict]:
        """Decode JPEG or H.264 encoded image received on DATA_NAMESPACE.

        Args:
            data (Dict[str, Any]): Received dictionary with frame data.
            event (str): Event name.
            sid (str, optional): Namespace sid - only on the server side.
        """

        if "timestamp" in data:
            timestamp = data["timestamp"]
        else:
            logger.info("Timestamp not set, setting default value")
            timestamp = 0

        if "frame" not in data:
            logger.error("Data does not contain frame.")
            self.send_data(
                {"timestamp": timestamp, "error": "Data does not contain frame."},
                self._callbacks_info[event].error_event,
                sid=sid,
            )
            return None

        eio_sid = self.get_client_eio_sid(sid, DATA_NAMESPACE)
        if self._callbacks_info[event].type is ChannelType.H264 and eio_sid not in self._decoders:
            if "width" not in data or "height" not in data:
                logger.error("Data does not contain width or height, it is mandatory for H.264.")
                self.send_data(
                    {
                        "timestamp": timestamp,
                        "error": "Data does not contain width or height, it is mandatory for H.264.",
                    },
                    self._callbacks_info[event].error_event,
                    sid=sid,
                )
                return None
            try:
                logger.info(f"Creating H.264 decoder for image size {data['width']}x{data['height']}")
                self._decoders[eio_sid] = H264Decoder(data["width"], data["height"])
            except Exception as e:
                logger.error(f"Cannot create H.264 decoder: {repr(e)}")
                self.send_data(
                    {"timestamp": timestamp, "error": f"Cannot create H.264 decoder: {repr(e)}"},
                    self._callbacks_info[event].error_event,
                    sid=sid,
                )
                return None

        if eio_sid in self._decoders:
            last_timestamp = self._decoders[eio_sid].last_timestamp
            if timestamp - last_timestamp < 0:
                logger.error(
                    f"Received frame with older timestamp: {timestamp}, "
                    f"last_timestamp: {last_timestamp}, diff: {timestamp - last_timestamp}"
                )
                self.send_data(
                    {
                        "timestamp": timestamp,
                        "error": f"Received frame with older timestamp: {timestamp}, "
                        f"last_timestamp: {last_timestamp}, diff: {timestamp - last_timestamp}",
                    },
                    self._callbacks_info[event].error_event,
                    sid=sid,
                )
                return None
            self._decoders[eio_sid].last_timestamp = timestamp

        if eio_sid in self._decoders:
            try:
                frame_decoded = self._decoders[eio_sid].decode_packet_data(data["frame"])
            except H264DecoderError as e:
                logger.error(f"H.264 decoder error: {e}")
                # Try to recreate decoder
                if self._decoders[eio_sid].get_init_count() < self._recreate_h264_attempts_count:
                    logger.info(f"Try to recreate decoder ... attempt {self._decoders[eio_sid].get_init_count()}")
                    self._decoders[eio_sid].decoder_init()
                self.send_data(
                    {"timestamp": timestamp, "error": f"H.264 decoder error: {e}"},
                    self._callbacks_info[event].error_event,
                    sid=sid,
                )
                return None
        else:
            try:
                frame_decoded = cv2.imdecode(np.frombuffer(data["frame"], dtype=np.uint8), cv2.IMREAD_COLOR)
            except Exception as e:
                logger.error(f"Failed to decode frame data: {repr(e)}")
                self.send_data(
                    {"timestamp": timestamp, "error": f"Failed to decode frame data: {repr(e)}"},
                    self._callbacks_info[event].error_event,
                    sid=sid,
                )
                return None

        decoded_data = {"frame": frame_decoded, "timestamp": timestamp}
        if "metadata" in data:
            decoded_data["metadata"] = data["metadata"]

        return decoded_data

    @property
    def stats(self):
        return self._stats

    @property
    def sizes(self):
        return self._sizes

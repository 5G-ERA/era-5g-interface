import logging
from typing import Dict, Optional

import numpy as np
from av.codec import CodecContext
from av.error import FFmpegError
from av.packet import Packet
from av.video.codeccontext import VideoCodecContext
from av.video.frame import VideoFrame


class FrameEncoderError(Exception):
    """FrameEncoderError Exception."""

    pass


# TODO: only for testing purpose
# from pathlib import Path
# Path("input").mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("Video frame encoder")


class FrameEncoder:
    """Video frame Encoder."""

    def __init__(
        self, width: int, height: int, fps: float = 30, codec: str = "h264", options: Optional[Dict[str, str]] = None
    ) -> None:
        """Constructor.

        Args:
            width (int): Video frame width.
            height (int): Video frame height.
            fps (float): Video framerate (FPS), default: 30.
            codec (str): Video codec name, e.g. h264, hevc, or vp9, default: h264.
            options (Dict[str, str], optional): Codec options, e.g. {"crf": "0", "preset": "ultrafast",
                "tune": "zerolatency", "x264-params": "keyint=5"}, default: {"preset": "ultrafast",
                "tune": "zerolatency"}.
        """

        # Some default options.
        if options is None:
            if codec == "h264":
                options = {"preset": "ultrafast", "tune": "zerolatency"}
            elif codec == "hevc":
                options = {"crf": "10", "preset": "ultrafast", "tune": "zerolatency", "x265-params": "frame-threads=1"}
            elif codec == "vp9":
                options = {"quality": "realtime", "speed": "8", "lag-in-frames": "0"}
        logger.debug(f"Encoder ({codec}) options: {options}")

        # TODO: only for testing purpose
        # options = {"crf": "0", "preset": "ultrafast", "tune": "zerolatency"}
        # options = {"preset": "ultrafast", "tune": "zerolatency", "x264-params": "keyint=5"}
        # self.frame_id = 0

        self._fps = fps
        self._width = width
        self._height = height
        self._options = options
        self._pix_fmt = "yuv420p"
        self._encoder: VideoCodecContext = CodecContext.create(codec, "w")
        self._init_count = 0
        self.last_timestamp: int = 0
        self._last_frame_is_keyframe = False
        self.encoder_init()

    def width(self) -> int:
        """Get video frame width.

        Returns:
            Video frame width.
        """

        return self._width

    def height(self) -> int:
        """Get video frame height.

        Returns:
            Video frame height.
        """

        return self._height

    def fps(self) -> float:
        """Get video framerate.

        Returns:
            Video framerate.
        """

        return self._fps

    def encoder_init(self) -> None:
        """Init video encoder."""

        self._init_count += 1
        if self._encoder.is_open:
            self._encoder.close()
        self._encoder.width = self._width
        self._encoder.height = self._height
        self._encoder.framerate = self._fps
        self._encoder.pix_fmt = self._pix_fmt
        self._encoder.options = self._options
        self._encoder.open()

    def get_init_count(self) -> int:
        """Get encoder init attempts count.

        Returns:
            Encoder init attempts count.
        """

        return self._init_count

    def last_frame_is_keyframe(self) -> bool:
        """Is last frame a keyframe?

        Returns:
            True if last frame is keyframe.
        """

        return self._last_frame_is_keyframe

    def encode_ndarray(self, frame_data: np.ndarray, format: str = "bgr24") -> bytes:
        """Encode ndarray to packets bytes.

        Args:
            frame_data (ndarray): Video frame / image.
            format (str): Image format.

        Returns:
            Packet data.
        """

        try:
            frame = VideoFrame.from_ndarray(frame_data, format=format)
            # TODO: only for testing purpose
            # frame.to_image().save("input/frame-%04d.jpg" % self.frame_id)
            # self.frame_id += 1

            self._last_frame_is_keyframe = False
            packets = []
            packet: Packet
            for packet in self._encoder.encode(frame):
                # TODO: only for testing purpose
                logger.debug(f"Frame {frame} encoded to packet: {packet}")
                logger.debug(
                    f"packet.pts: {packet.pts}, "
                    f"packet.dts: {packet.dts}, "
                    f"packet.key_frame: {packet.is_keyframe}, "
                    f"packet.is_corrupt: {packet.is_corrupt}"
                )
                if packet.is_keyframe:
                    self._last_frame_is_keyframe = True
                packets.append(bytes(packet))

            # TODO: only for testing purpose
            # if len(packets) == 0:
            #    raise FFmpegError(tag_to_code(b"INDA"), f"No packet encoded from frame {frame}")

            if len(packets) > 1:
                logger.info(f"Frame {frame} encoded to multiple packets: {packets}")
            return b"".join(packets)
        except FFmpegError as e:
            raise FrameEncoderError(e)

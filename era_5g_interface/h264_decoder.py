import logging

import numpy as np
from av.codec import CodecContext
from av.error import FFmpegError, tag_to_code
from av.packet import Packet
from av.video.codeccontext import VideoCodecContext
from av.video.frame import VideoFrame


class H264DecoderError(Exception):
    """H264DecoderError Exception."""

    pass


# TODO: only for testing purpose
# Path("output").mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("H.264 decoder")


class H264Decoder:
    """H.264 Decoder."""

    def __init__(self, width: int, height: int, fps: float = 30) -> None:
        """Constructor.

        Args:
            width (int): Video frame width.
            height (int): Video frame height.
            fps (float): Video framerate (FPS), default: 30.
        """
        self._fps = fps
        self._width = width
        self._height = height
        self._pix_fmt = "yuv420p"
        self._decoder: VideoCodecContext = CodecContext.create("h264", "r")
        self._init_count = 0
        self.last_timestamp: int = 0
        self._last_frame_is_keyframe = False
        self.decoder_init()

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

    def decoder_init(self) -> None:
        """Init H.264 decoder."""

        self._init_count += 1
        self._decoder = CodecContext.create("h264", "r")
        self._decoder.width = self._width
        self._decoder.height = self._height
        self._decoder.framerate = self._fps
        self._decoder.pix_fmt = self._pix_fmt

    def get_init_count(self) -> int:
        """Get decoder init attempts count.

        Returns:
            Decoder init attempts count.
        """

        return self._init_count

    def last_frame_is_keyframe(self) -> bool:
        """Is last frame a keyframe?

        Returns:
            True if last frame is keyframe.
        """

        return self._last_frame_is_keyframe

    def decode_packet_data(self, packet_data: bytes, format: str = "bgr24") -> np.ndarray:
        """Decode H.264 packets bytes to ndarray.

        Args:
            packet_data (bytes): Packet data.
            format (str): Image format.

        Returns:
            Video frame / image.
        """

        try:
            packet = Packet(packet_data)

            # Multiple frames? - This should not happen because on the encoders side one frame is always encoded and sent
            frame: VideoFrame
            for frame in self._decoder.decode(packet):
                # TODO: only for testing purpose
                # logger.debug(f"Frame {frame} with id {frame.index} decoded from packet: {packet}")
                # logger.debug(
                #    f"frame.pts: {frame.pts}, "
                #    f"frame.dts: {frame.dts}, "
                #    f"frame.index: {frame.index}, "
                #    f"frame.key_frame: {frame.key_frame}, "
                #    f"frame.is_corrupt: {frame.is_corrupt}, "
                #    f"frame.time: {frame.time}"
                # )
                # TODO: only for testing purpose
                # frame.to_image().save('output/frame-%04d.jpg' % frame.index)

                self._last_frame_is_keyframe = frame.key_frame
                frame_ndarray: np.ndarray = frame.to_ndarray(format=format)
                return frame_ndarray
            # Sometimes, with dropping some TCP packets, no frame is decoded from av.Packet while no FFmpegError is
            # raised. This is resolved by throwing this exception.
            raise FFmpegError(tag_to_code(b"INDA"), f"No frame decoded from packet {packet}")
        except FFmpegError as e:
            raise H264DecoderError(e)

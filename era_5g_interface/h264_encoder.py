import logging

import av
import numpy as np
from av.codec import CodecContext
from av.error import FFmpegError
from av.video.codeccontext import VideoCodecContext


class H264EncoderError(FFmpegError):
    """FFmpegError Exception."""

    pass


# TODO: only for testing purpose
# Path("input").mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("H264 encoder")


class H264Encoder:
    def __init__(self, fps: float, width: int, height: int) -> None:
        self.encoder: VideoCodecContext = CodecContext.create("h264", "w")
        self.encoder.width = width
        self.encoder.height = height
        self.encoder.framerate = fps
        self.encoder.pix_fmt = "yuv420p"
        # TODO: only for testing purpose
        # self.encoder.options = {"crf": "0", "preset": "ultrafast", "tune": "zerolatency"}
        # self.encoder.options = {"preset": "ultrafast", "tune": "zerolatency","x264-params": "keyint=5"}
        # self.frame_id = 0
        self.encoder.options = {"preset": "ultrafast", "tune": "zerolatency"}

    def encode_ndarray(self, frame_data: np.ndarray, format: str = "bgr24"):
        frame = av.VideoFrame.from_ndarray(frame_data, format=format)
        # TODO: only for testing purpose
        # frame.to_image().save('input/frame-%04d.jpg' % self.frame_id)
        # self.frame_id += 1
        packets = []
        for packet in self.encoder.encode(frame):
            # TODO: only for testing purpose
            # logger.info(f"Frame {frame} encoded to packet: {packet}")
            packets.append(bytes(packet))
        if len(packets) > 1:
            logger.info(f"Frame {frame} encoded to multiple packets: {packets}")
        return b"".join(packets)

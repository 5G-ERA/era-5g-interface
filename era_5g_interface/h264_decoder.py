import logging

from av import Packet
from av.codec import CodecContext
from av.video.codeccontext import VideoCodecContext

# TODO: only for testing purpose
# Path("output").mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("H264 decoder")


class H264Decoder:
    def __init__(self, fps: float, width: int, height: int) -> None:
        self.decoder: VideoCodecContext = CodecContext.create("h264", "r")
        self.decoder.width = width
        self.decoder.height = height
        self.decoder.framerate = fps
        self.decoder.pix_fmt = "yuv420p"

    def decode_packet_data(self, packet_data, format: str = "bgr24"):
        packet = Packet(packet_data)
        # TODO: only for testing purpose
        # logger.info(f"Decoding packet: {packet}")
        # Multiple frames? - This should not happen because on the encoders side one frame is always encoded and sent
        for frame in self.decoder.decode(packet):
            # TODO: only for testing purpose
            # logger.info(f"Frame {frame} with id {frame.index} decoded from packet: {packet}")
            # logger.info(f"frame.pts: {frame.pts}, frame.dts: {frame.dts}, frame.index: {frame.index}, "
            #            f"frame.key_frame: {frame.key_frame}, frame.is_corrupt: {frame.is_corrupt}, "
            #            f"frame.time: {frame.time}")
            # frame.to_image().save('output/frame-%04d.jpg' % frame.index)
            return frame.to_ndarray(format=format)

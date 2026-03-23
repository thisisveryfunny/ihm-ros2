"""
Camera node: captures video from the Pi camera and streams it via WebRTC.

Uses the web server's WebSocket at /ws?role=robot for signaling (offer/answer/ICE exchange).
The actual video is sent peer-to-peer over UDP via WebRTC.

Configuration (environment variables):
  SERVER_URL    WebSocket server host (default "localhost:5173")
  CAMERA_INDEX  V4L2 camera device index (default 0)
  FRAME_WIDTH   Capture width (default 640)
  FRAME_HEIGHT  Capture height (default 480)
  FPS           Target frames per second (default 30)
"""

import asyncio
import json
import os
import logging

import cv2
import numpy as np
from av import VideoFrame

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaStreamTrack

try:
    import websockets
except ImportError:
    # Fall back to websockets from aiortc's dependencies
    import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('camera_node')

SERVER_URL = os.environ.get('SERVER_URL', 'localhost:5173')
CAMERA_INDEX = int(os.environ.get('CAMERA_INDEX', '0'))
FRAME_WIDTH = int(os.environ.get('FRAME_WIDTH', '640'))
FRAME_HEIGHT = int(os.environ.get('FRAME_HEIGHT', '480'))
FPS = int(os.environ.get('FPS', '30'))


class CameraVideoTrack(MediaStreamTrack):
    """A video track that reads frames from a V4L2 camera via OpenCV."""

    kind = 'video'

    def __init__(self):
        super().__init__()
        self._cap = cv2.VideoCapture(CAMERA_INDEX)
        # Use MJPEG for lower latency from the camera
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, FPS)

        if not self._cap.isOpened():
            raise RuntimeError(f'Cannot open camera at index {CAMERA_INDEX}')

        self._frame_interval = 1.0 / FPS
        self._timestamp = 0
        logger.info(f'Camera opened: {FRAME_WIDTH}x{FRAME_HEIGHT} @ {FPS}fps')

    async def recv(self):
        """Called by aiortc to get the next video frame."""
        # Pace frames to target FPS
        pts, time_base = await self.next_timestamp()

        ret, frame = self._cap.read()
        if not ret:
            # Return a black frame if capture fails
            frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)

        # Convert BGR (OpenCV) to RGB (av/WebRTC)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame_rgb, format='rgb24')
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame

    def stop(self):
        super().stop()
        if self._cap.isOpened():
            self._cap.release()
            logger.info('Camera released')


async def run():
    """Main async loop: connect to signaling WS, wait for offers, create WebRTC answers."""
    ws_url = f'ws://{SERVER_URL}/ws?role=robot'

    while True:
        try:
            logger.info(f'Connecting to signaling server: {ws_url}')
            async with websockets.connect(ws_url) as ws:
                logger.info('Signaling WebSocket connected')

                pc = None
                video_track = None

                async for raw in ws:
                    msg = json.loads(raw)
                    msg_type = msg.get('type')

                    if msg_type == 'webrtc-offer':
                        # Close previous peer connection if any
                        if pc:
                            await pc.close()
                        if video_track:
                            video_track.stop()

                        pc = RTCPeerConnection()
                        video_track = CameraVideoTrack()
                        pc.addTrack(video_track)

                        @pc.on('icecandidate')
                        async def on_ice(candidate):
                            if candidate:
                                await ws.send(json.dumps({
                                    'type': 'webrtc-ice',
                                    'candidate': candidate.candidate,
                                    'sdpMid': candidate.sdpMid,
                                    'sdpMLineIndex': candidate.sdpMLineIndex,
                                }))

                        offer = RTCSessionDescription(sdp=msg['sdp'], type='offer')
                        await pc.setRemoteDescription(offer)

                        answer = await pc.createAnswer()
                        await pc.setLocalDescription(answer)

                        await ws.send(json.dumps({
                            'type': 'webrtc-answer',
                            'sdp': pc.localDescription.sdp,
                        }))
                        logger.info('WebRTC answer sent')

                    elif msg_type == 'webrtc-ice' and pc:
                        try:
                            candidate = RTCIceCandidate(
                                sdpMid=msg.get('sdpMid'),
                                sdpMLineIndex=msg.get('sdpMLineIndex'),
                                candidate=msg['candidate'],
                            )
                            await pc.addIceCandidate(candidate)
                        except Exception as e:
                            logger.warning(f'Failed to add ICE candidate: {e}')

                    # Ignore other message types (command, status, etc.)

                # WebSocket closed
                if pc:
                    await pc.close()
                if video_track:
                    video_track.stop()

        except websockets.exceptions.ConnectionClosed:
            logger.info('Signaling WebSocket closed')
        except Exception as e:
            logger.error(f'Error: {e}')

        logger.info('Reconnecting in 2 seconds...')
        await asyncio.sleep(2)


def main():
    asyncio.run(run())


if __name__ == '__main__':
    main()

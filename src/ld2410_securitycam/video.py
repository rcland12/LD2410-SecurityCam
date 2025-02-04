import os

# import subprocess
import time
from datetime import datetime

# from pathlib import Path
from threading import Lock
from typing import Tuple

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput

from ld2410_securitycam.logger import logger

# class VideoRecorder:
#     """
#     Video recorder class for the Raspberry Pi camera.

#     Handles video recording with customizable parameters and H264 to MP4 conversion.
#     """

#     def __init__(
#         self,
#         width: int,
#         height: int,
#         fps: int,
#         zoom: Tuple[float],
#         rotation: int,
#         hflip: bool,
#         vflip: bool,
#         recordings_path: str,
#     ):
#         """
#         Initialize the video recorder.

#         Args:
#             width (int): Video width in pixels
#             height (int): Video height in pixels
#             fps (int): Frames per second
#             zoom (Tuple[float]): Tuple of (x, y, width, height) for digital zoom
#             rotation (int): Image rotation in degrees
#             hflip (bool): Horizontal flip
#             vflip (bool): Vertical flip
#             recordings_path (str): Path to save recordings
#         """

#         self.width = width
#         self.height = height
#         self.fps = fps
#         self.zoom = zoom
#         self.rotation = rotation
#         self.hflip = hflip
#         self.vflip = vflip
#         self.picam2 = None
#         self.recording_lock = Lock()
#         self.recordings_path = recordings_path
#         self.is_recording = False

#     def initialize_camera(self) -> None:
#         """
#         Initialize the camera with configured settings.
#         """

#         if self.picam2 is None:
#             self.picam2 = Picamera2()
#             video_config = self.picam2.create_video_configuration(
#                 main={"size": (self.width, self.height), "format": "RGB888"},
#                 controls={"FrameRate": self.fps},
#             )
#             self.picam2.configure(video_config)

#             if self.rotation:
#                 self.picam2.set_controls({"RotateImage": self.rotation})

#             if self.zoom != (0.0, 0.0, 1.0, 1.0):
#                 x, y, w, h = self.zoom
#                 crop = (
#                     int(x * self.width),
#                     int(y * self.height),
#                     int(w * self.width),
#                     int(h * self.height),
#                 )
#                 self.picam2.set_controls({"ScalerCrop": crop})

#             if self.hflip:
#                 self.picam2.set_controls({"HFlip": True})
#             if self.vflip:
#                 self.picam2.set_controls({"VFlip": True})

#     def convert_to_mp4(self, h264_path: str) -> str:
#         """
#         Convert H264 file to MP4 format.

#         Args:
#             h264_path (str): Path to the H264 file

#         Returns:
#             str: Path to the converted MP4 file or original H264 file if conversion fails
#         """

#         try:
#             mp4_path = h264_path.replace(".h264", ".mp4")
#             subprocess.run(["MP4Box", "-add", h264_path, mp4_path], check=True)

#             Path(h264_path).unlink()
#             return mp4_path
#         except subprocess.CalledProcessError as e:
#             logger.error(f"Error converting to MP4: {e}")
#             return h264_path
#         except Exception as e:
#             logger.error(f"Unexpected error during conversion: {e}")
#             return h264_path

#     def __call__(self, duration=30):
#         with self.recording_lock:
#             if self.is_recording:
#                 logger.info("Already recording, skipping this trigger")
#                 return None

#             self.is_recording = True

#         try:
#             if not self.picam2:
#                 self.initialize_camera()

#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             mp4_filename = os.path.join(self.recordings_path, f"motion_{timestamp}.mp4")

#             encoder = FFmpegEncoder(mp4_filename)

#             self.picam2.start()
#             logger.info(f"Starting {duration} second recording...")
#             self.picam2.start_recording(encoder)
#             time.sleep(duration)
#             self.picam2.stop_recording()
#             logger.info("Recording complete")

#             return mp4_filename

#         except Exception as e:
#             logger.error(f"Error during recording: {e}")
#             return None

#         finally:
#             with self.recording_lock:
#                 self.is_recording = False

#     # def __call__(self, duration=30):
#     #     with self.recording_lock:
#     #         if self.is_recording:
#     #             logger.info("Already recording, skipping this trigger")
#     #             return None

#     #         self.is_recording = True

#     #     try:
#     #         if not self.picam2:
#     #             self.initialize_camera()

#     #         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     #         h264_filename = os.path.join(
#     #             self.recordings_path, f"motion_{timestamp}.h264"
#     #         )

#     #         encoder = H264Encoder(bitrate=8000000, repeat=False, iperiod=15)

#     #         self.picam2.start()
#     #         logger.info(f"Starting {duration} second recording...")
#     #         self.picam2.start_recording(encoder, h264_filename)
#     #         time.sleep(duration)
#     #         self.picam2.stop_recording()
#     #         logger.info("Recording complete. Converting to MP4...")

#     #         return self.convert_to_mp4(h264_filename)

#     #     except Exception as e:
#     #         logger.error(f"Error during recording: {e}")
#     #         return None

#     #     finally:
#     #         with self.recording_lock:
#     #             self.is_recording = False

#     def cleanup(self) -> None:
#         """
#         Clean up resources for PiCamera2.
#         """

#         if self.picam2:
#             self.picam2.close()
#             self.picam2 = None


class VideoRecorder:
    """
    Video recorder class for the Raspberry Pi camera.

    Handles video recording with customizable parameters and direct MP4 recording.
    """

    def __init__(
        self,
        width: int,
        height: int,
        fps: int,
        zoom: Tuple[float],
        rotation: int,
        hflip: bool,
        vflip: bool,
        recordings_path: str,
    ):
        """Initialize with the same parameters as before"""
        self.width = width
        self.height = height
        self.fps = fps
        self.zoom = zoom
        self.rotation = rotation
        self.hflip = hflip
        self.vflip = vflip
        self.picam2 = None
        self.recording_lock = Lock()
        self.recordings_path = recordings_path
        self.is_recording = False

    def initialize_camera(self) -> None:
        """
        Initialize the camera with configured settings.
        """
        if self.picam2 is None:
            self.picam2 = Picamera2()
            video_config = self.picam2.create_video_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"},
                controls={"FrameRate": self.fps},
            )
            self.picam2.configure(video_config)

            if self.rotation:
                self.picam2.set_controls({"RotateImage": self.rotation})

            if self.zoom != (0.0, 0.0, 1.0, 1.0):
                x, y, w, h = self.zoom
                crop = (
                    int(x * self.width),
                    int(y * self.height),
                    int(w * self.width),
                    int(h * self.height),
                )
                self.picam2.set_controls({"ScalerCrop": crop})

            if self.hflip:
                self.picam2.set_controls({"HFlip": True})
            if self.vflip:
                self.picam2.set_controls({"VFlip": True})

    def __call__(self, duration=30):
        """Record video for specified duration"""
        with self.recording_lock:
            if self.is_recording:
                logger.info("Already recording, skipping this trigger")
                return None

            self.is_recording = True

        try:
            if not self.picam2:
                self.initialize_camera()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mp4_filename = os.path.join(self.recordings_path, f"motion_{timestamp}.mp4")

            encoder = H264Encoder(1900000)
            output = FfmpegOutput(mp4_filename)

            self.picam2.start()
            logger.info(f"Starting {duration} second recording...")
            self.picam2.start_recording(encoder=encoder, output=output)
            time.sleep(duration)
            self.picam2.stop_recording()
            logger.info("Recording complete")

            return mp4_filename

        except Exception as e:
            logger.error(f"Error during recording: {e}")
            return None

        finally:
            with self.recording_lock:
                self.is_recording = False

    def cleanup(self) -> None:
        """Clean up resources"""
        if self.picam2:
            self.picam2.close()
            self.picam2 = None

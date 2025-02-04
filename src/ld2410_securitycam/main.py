import os
import time
from typing import Tuple

from dotenv import load_dotenv

from ld2410_securitycam.ftp import FTPUploader
from ld2410_securitycam.logger import logger
from ld2410_securitycam.motion import LD2410UART, SensorData
from ld2410_securitycam.utils import EnvArgumentParser
from ld2410_securitycam.video import VideoRecorder


def main(
    video_duration: int,
    recordings_path: str,
    camera_width: int,
    camera_height: int,
    camera_fps: int,
    camera_zoom: Tuple[float],
    camera_rotation: int,
    camera_hflip: bool,
    camera_vflip: bool,
    ftp_enabled: bool,
    ftp_host: str,
    ftp_port: int,
    ftp_username: str,
    ftp_password: str,
    ftp_remote_path: str,
) -> None:
    """
    Main function to run the motion detection and recording system.

    This function initializes and manages the video recorder and optional FTP uploader.
    It sets up motion detection monitoring and handles the recording and uploading
    of videos when motion is detected.

    Args:
        video_duration (int): Length of video recordings in seconds
        recordings_path (str): Directory path to store recordings
        camera_width (int): Camera resolution width in pixels
        camera_height (int): Camera resolution height in pixels
        camera_fps (int): Camera frames per second
        camera_zoom (Tuple[float]): Camera zoom settings as (x, y, width, height)
        camera_rotation (int): Camera rotation in degrees
        camera_hflip (bool): Whether to horizontally flip the camera image
        camera_vflip (bool): Whether to vertically flip the camera image
        ftp_enabled (bool): Whether to enable FTP uploads
        ftp_host (str): FTP server hostname
        ftp_port (int): FTP server port
        ftp_username (str): FTP account username
        ftp_password (str): FTP account password
        ftp_remote_path (str): Path to upload on remote FTP server
    """

    recorder = VideoRecorder(
        width=camera_width,
        height=camera_height,
        fps=camera_fps,
        zoom=camera_zoom,
        rotation=camera_rotation,
        hflip=camera_hflip,
        vflip=camera_vflip,
        recordings_path=recordings_path,
    )

    uploader = None
    if ftp_enabled:
        uploader = FTPUploader(
            host=ftp_host,
            username=ftp_username,
            password=ftp_password,
            port=ftp_port,
            ftp_remote_path=ftp_remote_path,
        )

    last_recording_time = 0
    RECORDING_COOLDOWN = 5

    def on_detection(sensor_data: SensorData) -> None:
        """
        Callback function triggered when motion is detected.

        This function handles the recording and optional uploading of video
        when motion is detected, respecting the cooldown period between recordings.

        Args:
            sensor_data (SensorData): Object containing sensor detection data including
                timestamp, distance, and signal strength
        """

        nonlocal last_recording_time
        current_time = time.time()

        if current_time - last_recording_time < RECORDING_COOLDOWN:
            return

        logger.info("\nTarget Detected!")
        logger.info(
            f"Time: {time.strftime('%H:%M:%S', time.localtime(sensor_data.timestamp))}"
        )

        if sensor_data.moving_target:
            logger.info(
                f"Moving target at {sensor_data.distance}cm (strength: {sensor_data.signal_strength})"
            )
        if sensor_data.stationary_target:
            logger.info(
                f"Stationary target at {sensor_data.distance}cm (strength: {sensor_data.signal_strength})"
            )

        filename = recorder(duration=video_duration)
        if filename:
            last_recording_time = current_time

            if ftp_enabled and uploader:
                success = uploader(local_path=filename)
                if not success and os.path.exists(filename):
                    logger.info(f"Upload failed, keeping local file {filename}")
            else:
                logger.info(f"FTP disabled, keeping local file {filename}")

    with LD2410UART(debug=True) as sensor:
        try:
            sensor.start_monitoring(on_detection)
            logger.info("Monitoring for motion... Press Ctrl+C to stop")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nStopping...")
        finally:
            recorder.cleanup()
            if uploader:
                uploader.close()


if __name__ == "__main__":
    load_dotenv()
    parser = EnvArgumentParser()
    parser.add_arg("VIDEO_DURATION", default=30, d_type=int)
    parser.add_arg("RECORDINGS_PATH", default="/app/recordings", d_type=str)
    parser.add_arg("CAMERA_WIDTH", default=1920, d_type=int)
    parser.add_arg("CAMERA_HEIGHT", default=1080, d_type=int)
    parser.add_arg("CAMERA_FPS", default=30, d_type=int)
    parser.add_arg("CAMERA_ZOOM", default=(0.0, 0.0, 1.0, 1.0), d_type=tuple)
    parser.add_arg("CAMERA_ROTATION", default=0, d_type=int)
    parser.add_arg("CAMERA_HFLIP", default=False, d_type=bool)
    parser.add_arg("CAMERA_VFLIP", default=False, d_type=bool)
    parser.add_arg("FTP_ENABLED", default=True, d_type=bool)
    parser.add_arg("FTP_HOSTNAME", default="127.0.0.1", d_type=str)
    parser.add_arg("FTP_PORT", default=21, d_type=int)
    parser.add_arg("FTP_USERNAME", default="username", d_type=str)
    parser.add_arg("FTP_PASSWORD", default="password", d_type=str)
    parser.add_arg("FTP_REMOTE_PATH", default="/", d_type=str)
    args = parser.parse_args()

    main(
        video_duration=args.VIDEO_DURATION,
        recordings_path=args.RECORDINGS_PATH,
        camera_width=args.CAMERA_WIDTH,
        camera_height=args.CAMERA_HEIGHT,
        camera_fps=args.CAMERA_FPS,
        camera_zoom=args.CAMERA_ZOOM,
        camera_rotation=args.CAMERA_ROTATION,
        camera_hflip=args.CAMERA_HFLIP,
        camera_vflip=args.CAMERA_VFLIP,
        ftp_enabled=args.FTP_ENABLED,
        ftp_host=args.FTP_HOSTNAME,
        ftp_port=args.FTP_PORT,
        ftp_username=args.FTP_USERNAME,
        ftp_password=args.FTP_PASSWORD,
        ftp_remote_path=args.FTP_REMOTE_PATH,
    )

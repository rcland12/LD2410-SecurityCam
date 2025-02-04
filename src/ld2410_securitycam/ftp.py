import os
from ftplib import FTP
from threading import Lock

from ld2410_securitycam.logger import logger


class FTPUploader:
    """
    A class to handle FTP uploads with connection management and thread safety.

    This class maintains a single FTP connection and provides thread-safe upload
    capabilities. It automatically handles connection establishment and cleanup.
    """

    def __init__(
        self, host: str, username: str, password: str, port: int, ftp_remote_path: str
    ) -> None:
        """
        Initialize the FTP uploader with server credentials.

        Args:
            host (str): FTP server hostname
            username (str): FTP account username
            password (str): FTP account password
            port (int): FTP server port number, defaults to 21
            ftp_remote_path (str): Path to upload on remote FTP server
        """

        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.ftp = None
        self.ftp_remote_path = ftp_remote_path
        self.upload_lock = Lock()

    def connect(self) -> bool:
        """
        Establish a connection to the FTP server if not already connected.

        Returns:
            bool: True if connection is successful or already exists, False otherwise
        """

        try:
            if self.ftp is None:
                self.ftp = FTP()
                self.ftp.connect(self.host, self.port)
                self.ftp.login(self.username, self.password)
            return True
        except Exception as e:
            logger.error(f"FTP connection error: {e}")
            return False

    def __call__(self, local_path: str) -> bool:
        """
        Upload a file to the FTP server in a thread-safe manner.

        Args:
            local_path (str): Path to the local file to upload

        Returns:
            bool: True if upload was successful, False otherwise
        """

        with self.upload_lock:
            try:
                if not os.path.exists(local_path):
                    logger.info(f"Error: Local file {local_path} not found")
                    return False

                if not self.connect():
                    return False

                remote_file_path = os.path.join(
                    self.ftp_remote_path, local_path.split("/")[-1]
                )
                with open(local_path, "rb") as file:
                    self.ftp.storbinary(f"STOR {remote_file_path}", file)

                logger.info(f"Successfully uploaded {local_path} to remote server")

                os.remove(local_path)
                logger.info(f"Removed local file {local_path}")
                return True

            except Exception as e:
                logger.error(f"FTP upload error: {e}")
                return False

    def close(self):
        if self.ftp is not None:
            try:
                self.ftp.quit()
            except Exception:
                self.ftp.close()
            finally:
                self.ftp = None

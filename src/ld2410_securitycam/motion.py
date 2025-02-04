import binascii
import time
from dataclasses import dataclass
from threading import Event, Thread
from typing import Any, Callable, Dict, Optional, Tuple, Type

import RPi.GPIO as GPIO
import serial

from ld2410_securitycam.logger import logger


@dataclass
class SensorData:
    """
    Data class representing sensor readings from the LD2410 radar sensor.

    Attributes:
        moving_target (bool): Whether a moving target is detected
        stationary_target (bool): Whether a stationary target is detected
        distance (int): Distance to the target in centimeters
        signal_strength (int): Strength of the radar signal
        raw_data (bytes): Raw byte data from the sensor
        timestamp (float): Unix timestamp of the reading
    """

    moving_target: bool
    stationary_target: bool
    distance: int
    signal_strength: int
    raw_data: bytes
    timestamp: float


class LD2410UART:
    """
    Interface for the LD2410 radar sensor using UART communication.

    This class handles communication with the sensor, data parsing, and continuous
    monitoring with callback support.
    """

    def __init__(
        self,
        uart_device: str = "/dev/ttyS0",
        presence_pin: int = 17,
        baud_rate: int = 256000,
        debug: bool = False,
    ) -> None:
        """
        Initialize the LD2410S radar sensor using UART.

        Args:
            uart_device (str): Path to the UART device
            presence_pin (int): GPIO pin number for presence detection
            baud_rate (int): UART baud rate
            debug (bool): Enable debug output

        Raises:
            serial.SerialException: If UART device cannot be opened
        """

        self.debug = debug
        self.presence_pin = presence_pin

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.presence_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        if self.debug:
            logger.info(f"Opening UART device: {uart_device}")
            logger.info(f"Baud rate: {baud_rate}")

        try:
            self.uart = serial.Serial(
                port=uart_device,
                baudrate=baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
            )
            logger.info("Successfully opened UART device")
        except serial.SerialException as e:
            logger.error(f"Error opening UART: {e}")
            raise

        self._stop_event = Event()
        self._monitor_thread = None
        self._last_target_time = 0
        self._min_target_interval = 0.5

        time.sleep(1.0)

    def _parse_data_packet(self, data: bytes) -> Optional[SensorData]:
        """
        Parse a data packet from the sensor.

        Args:
            data (bytes): Raw byte data from the sensor

        Returns:
            Optional[SensorData]: Parsed SensorData object or None if parsing fails
        """

        try:
            if len(data) < 7:
                return None

            if data[0] != 0xF8 or data[-1] != 0xFE:
                return None

            target_state = data[1]
            distance = data[3]
            signal_strength = data[4]

            has_moving = (target_state & 0x01) != 0
            has_stationary = (target_state & 0x02) != 0

            return SensorData(
                moving_target=has_moving,
                stationary_target=has_stationary,
                distance=distance * 10,  # cm
                signal_strength=signal_strength,
                raw_data=data,
                timestamp=time.time(),
            )

        except Exception as e:
            if self.debug:
                logger.error(f"Error parsing packet: {e}")
            return None

    def _read_sensor(self) -> Optional[SensorData]:
        """
        Read and parse sensor data.

        Returns:
            Optional[SensorData]: Parsed SensorData object or None if no data is available
        """

        if not self.uart.in_waiting:
            return None

        raw_data = self.uart.read(self.uart.in_waiting)

        if self.debug:
            logger.info(
                f"Raw data received (hex): {binascii.hexlify(raw_data).decode()}"
            )

        packets = []
        for i in range(len(raw_data)):
            if raw_data[i] == 0xF8:
                if i + 6 < len(raw_data) and raw_data[i + 6] == 0xFE:
                    packets.append(raw_data[i : i + 7])

        if packets:
            return self._parse_data_packet(packets[-1])

        return None

    def _monitor_loop(
        self,
        callback_func: Callable[[SensorData], None],
        args: Tuple = (),
        kwargs: Dict[str, Any] = {},
    ) -> None:
        """
        Monitor the sensor data continuously.

        Args:
            callback_func (Callable[[SensorData], None]): Function to call when motion is detected
            args (Tuple): Additional positional arguments for the callback
            kwargs (Dict[str, Any]): Additional keyword arguments for the callback
        """

        if self.debug:
            logger.info("Starting monitoring loop...")
            logger.info("Waiting for sensor data...")

        while not self._stop_event.is_set():
            try:
                sensor_data = self._read_sensor()
                current_time = time.time()

                if sensor_data:
                    if (
                        current_time - self._last_target_time
                    ) >= self._min_target_interval:
                        if sensor_data.moving_target or sensor_data.stationary_target:
                            self._last_target_time = current_time
                            try:
                                callback_func(sensor_data)
                            except Exception as e:
                                logger.info(f"Error in callback: {e}")

            except Exception as e:
                logger.error(f"Error reading sensor: {e}")

            time.sleep(0.05)

    def start_monitoring(
        self, callback_func: Callable[[SensorData], None], *args: Any, **kwargs: Any
    ) -> None:
        """
        Start monitoring the sensor.

        Args:
            callback_func (Callable[[SensorData], None]): Function to call when motion is detected
            *args (Any): Additional positional arguments for the callback
            **kwargs (Any): Additional keyword arguments for the callback
        """

        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            logger.info("Already monitoring!")
            return

        logger.info("Starting sensor monitoring...")
        self._stop_event.clear()
        self._monitor_thread = Thread(
            target=self._monitor_loop, args=(callback_func, args, kwargs), daemon=True
        )
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        """
        Stop monitoring the sensor.
        """

        logger.info("Stopping monitoring...")
        self._stop_event.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join()
        self._monitor_thread = None

    def cleanup(self) -> None:
        """
        Clean up resources and GPIO pins.
        """

        self.stop_monitoring()
        if hasattr(self, "uart") and self.uart.is_open:
            self.uart.close()
        GPIO.cleanup()

    def __enter__(self) -> "LD2410UART":
        """
        Context manager entry.
        """

        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """
        Context manager exit.
        """

        self.cleanup()

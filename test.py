import threading
import time
from dataclasses import dataclass
from threading import Thread
from typing import Any, Callable, Dict, Optional, Tuple, Type

import serial

from logger import logger


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
    def __init__(
        self,
        uart_device: str = "/dev/ttyS0",
        baud_rate: int = 115200,
        motion_threshold: int = 140,
        debug: bool = False,
    ):
        self.debug = debug
        self.motion_threshold = motion_threshold
        self._stop_event = threading.Event()
        self._monitor_thread = None

        try:
            self.uart = serial.Serial(
                port=uart_device,
                baudrate=baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
            )
            if self.debug:
                logger.info(f"Successfully opened UART device: {uart_device}")
        except serial.SerialException as e:
            logger.error(f"Error opening UART: {e}")
            raise

        time.sleep(1.0)

    def _read_sensor(self) -> Optional[SensorData]:
        """Read and parse sensor data."""
        try:
            buffer = bytearray()
            while True:
                if len(buffer) >= 4:
                    if buffer[-4:] == b"\x00bn\x02":
                        break
                b = self.uart.read(1)
                if not b:
                    return None
                buffer.extend(b)

            signal_byte = self.uart.read(1)
            if not signal_byte:
                return None

            signal_strength = signal_byte[0]

            moving_target = signal_strength >= self.motion_threshold
            stationary_target = False

            return SensorData(
                moving_target=moving_target,
                stationary_target=stationary_target,
                distance=0,
                signal_strength=signal_strength,
                raw_data=buffer[-4:] + signal_byte,
                timestamp=time.time(),
            )

        except serial.SerialException as e:
            if self.debug:
                logger.error(f"Serial error: {e}")
            return None

    def _monitor_loop(
        self,
        callback_func: Callable[[SensorData], None],
        args: Tuple = (),
        kwargs: Dict[str, Any] = {},
    ) -> None:
        """Monitor the sensor data continuously."""
        if self.debug:
            logger.info("Starting monitoring loop...")
            logger.info("Waiting for sensor data...")

        while not self._stop_event.is_set():
            try:
                sensor_data = self._read_sensor()
                if sensor_data:
                    try:
                        callback_func(sensor_data)
                    except Exception as e:
                        logger.error(f"Error in callback: {e}")

            except Exception as e:
                logger.error(f"Error reading sensor: {e}")

            time.sleep(0.05)

    def start_monitoring(
        self, callback_func: Callable[[SensorData], None], *args: Any, **kwargs: Any
    ) -> None:
        """Start monitoring the sensor."""
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            logger.info("Already monitoring!")
            return

        logger.info("Starting sensor monitoring after delay...")
        self._stop_event.clear()
        self._monitor_thread = Thread(
            target=self._monitor_loop, args=(callback_func, args, kwargs), daemon=True
        )
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        """Stop monitoring the sensor."""
        logger.info("Stopping monitoring...")
        self._stop_event.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join()
        self._monitor_thread = None

    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_monitoring()
        if hasattr(self, "uart") and self.uart.is_open:
            self.uart.close()

    def __enter__(self) -> "LD2410UART":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        self.cleanup()


if __name__ == "__main__":

    def motion_callback(data: SensorData):
        print(f"Motion: {data.moving_target}", end=" ", flush=True)
        print(f"Stationary: {data.stationary_target}", end=" ", flush=True)
        print(f"Distance: {data.distance}", end=" ", flush=True)
        print(f"Signal Strength: {data.signal_strength}", end=" ", flush=True)
        print(f"Raw Data: {data.raw_data}", end=" ", flush=True)
        print(f"Timestamp: {data.timestamp}")

    try:
        # Create sensor with debug output and threshold of 140
        sensor = LD2410UART(debug=True, motion_threshold=140)

        # Start monitoring with callback
        sensor.start_monitoring(motion_callback)

        # Keep the main thread running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        sensor.cleanup()

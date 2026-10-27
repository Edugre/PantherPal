"""Background DHT22 reader.

The DHT22 is slow and flaky (reads fail often), so it is polled on its own
thread and the UI only ever looks at the latest good reading.
"""
import math
import random
import threading
import time
from dataclasses import dataclass

import config


@dataclass(frozen=True)
class Reading:
    temp_c: float
    humidity: float
    timestamp: float

    @property
    def temp_f(self):
        return self.temp_c * 9 / 5 + 32


class SensorService:
    def __init__(self, fake=False):
        self.fake = fake
        self._lock = threading.Lock()
        self._latest = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="dht22", daemon=True)
        self._device = None
        self.status = "starting"   # starting | ok | waiting | offline | fake

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=5)

    def latest(self):
        """Most recent reading, or None if there is none or it is stale."""
        with self._lock:
            reading = self._latest
        if reading is None or time.time() - reading.timestamp > config.SENSOR_STALE_AFTER:
            return None
        return reading

    def _set(self, temp_c, humidity):
        with self._lock:
            self._latest = Reading(temp_c, humidity, time.time())

    def _run(self):
        if self.fake:
            self._run_fake()
            return
        try:
            import adafruit_dht
            import board
            self._device = adafruit_dht.DHT22(getattr(board, config.DHT_PIN), use_pulseio=False)
        except Exception as exc:
            print(f"[sensor] DHT22 unavailable: {exc}")
            self.status = "offline"
            return

        try:
            while not self._stop.is_set():
                try:
                    temp_c = self._device.temperature
                    humidity = self._device.humidity
                    if temp_c is not None and humidity is not None:
                        self._set(temp_c, humidity)
                        self.status = "ok"
                except RuntimeError:
                    # Normal for a DHT22: checksum/timing errors. Retry next tick.
                    if self.latest() is None:
                        self.status = "waiting"
                except Exception as exc:
                    print(f"[sensor] unexpected error: {exc}")
                    self.status = "waiting"
                self._stop.wait(config.SENSOR_INTERVAL)
        finally:
            self._device.exit()

    def _run_fake(self):
        self.status = "fake"
        start = time.time()
        while not self._stop.is_set():
            t = time.time() - start
            self._set(22 + 3 * math.sin(t / 60) + random.uniform(-0.2, 0.2),
                      55 + 10 * math.sin(t / 90))
            self._stop.wait(config.SENSOR_INTERVAL)

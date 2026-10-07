"""Фоновый поток с asyncio: ждёт подключения iOS-устройства и стримит из него syslog."""
import asyncio
import queue
import threading

from pymobiledevice3 import usbmux
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.os_trace import OsTraceService

DEVICE_POLL_INTERVAL_S = 1.0


class LogBackend:
    """Крутится в отдельном потоке с собственным asyncio event loop:
    ждёт подключения устройства и стримит из него syslog."""

    def __init__(self, line_queue: queue.Queue, status_queue: queue.Queue):
        self.line_queue = line_queue
        self.status_queue = status_queue
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._monitor())

    async def _monitor(self):
        stream_task = None
        connected_serial = None
        while True:
            try:
                devices = await usbmux.list_devices()
            except Exception:
                devices = []
            usb_devices = [d for d in devices if d.is_usb]

            if usb_devices:
                serial = usb_devices[0].serial
                if stream_task is None or stream_task.done():
                    connected_serial = serial
                    self.status_queue.put(("connected", serial))
                    stream_task = self.loop.create_task(self._stream(serial))
            else:
                if connected_serial is not None:
                    connected_serial = None
                    self.status_queue.put(("disconnected", None))
                if stream_task is not None and not stream_task.done():
                    stream_task.cancel()
                stream_task = None

            await asyncio.sleep(DEVICE_POLL_INTERVAL_S)

    async def _stream(self, serial: str):
        try:
            lockdown = await create_using_usbmux(serial=serial)
            async for entry in OsTraceService(lockdown=lockdown).syslog():
                ts = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]
                # entry.level может быть 0 (NOTICE), а 0 - falsy, поэтому
                # сравнение именно с None (а не просто "if entry.level").
                level = entry.level.name if entry.level is not None else "-"
                process = entry.image_name or ""
                self.line_queue.put(f"{ts} {level:<7} {process}[{entry.pid}]: {entry.message}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.status_queue.put(("error", str(e)))

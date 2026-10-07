import struct
from pathlib import Path

ICON = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
WINDOWS_SIZES = {16, 24, 32, 48, 64, 128, 256}


def test_the_exe_icon_carries_every_windows_size():
    data = ICON.read_bytes()
    count = struct.unpack("<H", data[4:6])[0]
    sizes = set()
    for i in range(count):
        width = data[6 + 16 * i] or 256  # 0 means 256 in the ICO directory
        sizes.add(width)
    assert WINDOWS_SIZES <= sizes

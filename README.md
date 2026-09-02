# iOS Log Viewer

[![Latest release](https://img.shields.io/github/v/release/DmitryItigin/iOS_Logger)](https://github.com/DmitryItigin/iOS_Logger/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6)](https://github.com/DmitryItigin/iOS_Logger/releases/latest)

**View live console logs from an iPhone/iPad over USB — on Windows, no Mac, no Xcode.**

If you build or QA-test iOS apps but only have a Windows machine, there's no
`Console.app`, no `xcrun simctl`, no Xcode device console. This tool fills
that gap: plug your iOS device into your Windows PC over USB and watch its
syslog stream live in a lightweight desktop window — with search and
Logcat-style filtering, just like you'd expect from an Android tool.

### ⬇️ Download

No Python, no cloning — just grab the exe and run it:

**[Download the latest release](https://github.com/DmitryItigin/iOS_Logger/releases/latest)**

## Features

- **Live syslog streaming** from a USB-connected iOS device (via
  [`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3)) —
  auto-detects the device, reconnects automatically if it's unplugged and
  plugged back in.
- **Text filter, Logcat-style** — type in the filter box and only matching
  log lines stay visible, live, as new lines keep streaming in.
- **Log level filter** — a dropdown with checkboxes for `Fault` / `Error` /
  `User action` / `Notice` / `Info` / `Debug`, so you can isolate e.g. only
  errors with one click.
- **Find & highlight** (`Ctrl+F`) — jump between matches without hiding
  anything, always visible in the toolbar.
- **Pause / Resume**, **Clear**, and **Export to `.txt`** — export asks
  whether to save just the currently filtered lines or the whole capture.
- Keyboard shortcuts (`Ctrl+F`, `Ctrl+V`) work correctly regardless of
  keyboard layout (e.g. Russian), where Tkinter's default layout-dependent
  bindings normally break.

## Requirements

- Windows
- The Apple Mobile Device USB driver — installed automatically with
  **iTunes**, or with the **"Apple Devices"** app from the Microsoft Store
- An iOS device connected via USB, unlocked, with **"Trust This Computer"**
  accepted
- Python 3.9+ (only if running from source instead of the prebuilt exe)

## Running from source

Prefer this if you want to hack on the code instead of using the prebuilt exe.

```bash
git clone https://github.com/DmitryItigin/iOS_Logger.git
cd iOS_Logger
pip install -r requirements.txt
```

## Usage

Launch the app — double-click the downloaded exe, or run
`python ios_log_viewer.py` if you're running from source.

1. Connect your iOS device over USB and unlock it. Accept the "Trust This
   Computer?" prompt if it appears.
2. The status bar shows `Подключено: <serial>` once the device is detected
   and the log starts streaming.
3. Type in the **Фильтр (Filter)** box to show only matching lines; clear it
   (✕ or `Esc`) to see everything again.
4. Click **Уровни ▾ (Levels)** to show/hide specific log levels.
5. Use the **Найти (Find)** bar (always visible, or `Ctrl+F` to focus it) to
   highlight and jump between matches without hiding other lines.
6. **Пауза** stops ingesting new lines without losing what's already
   captured; **Очистить** clears the buffer; **Экспорт в файл** saves
   everything captured so far to a `.txt` file.

## Building a standalone .exe

The project ships with ready-made [PyInstaller](https://pyinstaller.org/)
spec files:

```bash
pip install pyinstaller
pyinstaller "iOS Log Viewer.spec"            # windowed build, with splash screen
pyinstaller "iOS_Log_Viewer_console.spec"    # console build, useful for debugging
```

The built executable will be under `dist/`.

## How it works

A background thread runs its own `asyncio` event loop, polling for a
USB-connected device via `pymobiledevice3.usbmux` and streaming its syslog
through `OsTraceService`. Log lines are pushed onto a thread-safe queue and
picked up by the Tkinter main loop roughly every 100 ms, so the UI never
blocks on device I/O.

## License

[MIT](LICENSE)

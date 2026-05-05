# Xiaomi HyperOS Bootloader Unlock Script

A high-precision Python script for unlocking Xiaomi HyperOS bootloaders. This script uses NTP synchronization and phase-shifting logic to hit the unlock request window with microsecond precision.

## Features
- **NTP Synchronization:** Automatically pings multiple NTP servers to synchronize with exact Beijing time (UTC+8).
- **Phase Shift Logic:** Accounts for network latency to fire requests exactly at the 00:00:00.000 reset window.
- **High-Precision Loop:** Uses sub-millisecond sleep intervals for perfect timing.

## Requirements
- **System:** Python 3.x
- **Network:** **VPS or a connection with very good ping is highly recommended** for best results.
- **Dependencies:** `requests`, `ntplib`, `pytz`, `urllib3`, `icmplib`, `colorama`

## Usage
1. Place your service token in a `token.txt` file.
2. Place your phase shift value (in ms) in a `timeshift.txt` file.
3. Run the script: `python unlock.py`
4. Enter the token line number when prompted.

## Disclaimer
This tool is for educational purposes only. Use it at your own risk.

# Build Windows executable (WSL + PyInstaller)

These steps let you build a Windows executable from WSL so you can double-click it on Windows.

## Prerequisites

- Windows Python installed (from python.org or Microsoft Store).
- `pip install --upgrade pip`
- Project dependencies installed.

## Steps

1. From WSL, install the dependencies into Windows Python and then PyInstaller:

   ```bash
   /mnt/c/Users/<YourUser>/AppData/Local/Programs/Python/Python311/python.exe -m pip install -r requirements.txt
   /mnt/c/Users/<YourUser>/AppData/Local/Programs/Python/Python311/python.exe -m pip install pyinstaller
   ```

2. Build the exe (replace the Python path with yours):

   ```bash
   /mnt/c/Users/<YourUser>/AppData/Local/Programs/Python/Python311/python.exe -m PyInstaller --noconsole --onefile gpu_monitor.py
   ```

3. The executable will be in `dist/gpu_monitor.exe`. Double-click it on Windows.

## Notes

- Make sure the Windows machine can reach the server over SSH (port 22 by default).
- If you prefer using WSL Python instead of Windows Python, you can build a Linux binary, but Windows cannot run it directly.

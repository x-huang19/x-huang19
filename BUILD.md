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

2. Build the exe (replace the Python path with yours). Use the `.pyw` entry point and `--windowed`/`--noconsole` so Windows does not show a command-line window when you double-click the EXE:

   ```bash
   /mnt/c/Users/<YourUser>/AppData/Local/Programs/Python/Python311/python.exe -m PyInstaller --windowed --noconsole --onefile --name gpu_monitor gpu_monitor.pyw
   ```

3. The executable will be in `dist/gpu_monitor.exe`. Double-click it on Windows; only the GUI window should appear.

## Notes

- Make sure the Windows machine can reach the server over SSH (port 22 by default).
- If you prefer using WSL Python instead of Windows Python, you can build a Linux binary, but Windows cannot run it directly.

## Troubleshooting (EXE won't open)

1. Run from Command Prompt to see errors:

   ```bash
   dist\\gpu_monitor.exe
   ```

2. Check the log file next to the EXE (`gpu_monitor.log`) for startup errors.
3. Ensure Microsoft Visual C++ Redistributable is installed (required by some Python wheels).
4. Windows Defender or antivirus may quarantine the EXE; restore/allow it if blocked.

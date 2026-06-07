"""
Cluely Stealth Launcher
========================
Runs Cluely WITHOUT a visible terminal window.
Double-click this file or run: pythonw start_cluely.pyw

The .pyw extension tells Windows to use pythonw.exe (no console).
No terminal, no taskbar entry, no visible evidence — just the overlay + hotkeys.
"""

import subprocess
import sys
import os

# Get the venv python path
script_dir = os.path.dirname(os.path.abspath(__file__))
venv_pythonw = os.path.join(script_dir, "venv", "Scripts", "pythonw.exe")
venv_python = os.path.join(script_dir, "venv", "Scripts", "python.exe")
main_py = os.path.join(script_dir, "main.py")

# Use pythonw (no console window) if available
python_exe = venv_pythonw if os.path.exists(venv_pythonw) else venv_python

# Launch detached from this process
subprocess.Popen(
    [python_exe, main_py],
    cwd=script_dir,
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

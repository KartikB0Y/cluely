# Cluely — Stealth Mode

How the panel stays invisible during meetings, how to verify it, and how to operate it when there's no visible UI to click.

---

## What stealth mode actually does

When `STEALTH_MODE = True` and `OVERLAY_EXCLUDE_FROM_CAPTURE = True` in `config.py` (both are ON by default), these protections are active:

| Layer | Mechanism | Effect |
|---|---|---|
| **Screen capture** | `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` | Window is invisible to Zoom share, Google Meet share, Teams share, OBS, Snipping Tool, PrintScreen, any DXGI/BitBlt capture |
| **Taskbar** | Qt `Tool` window flag | No taskbar icon. No Alt+Tab entry |
| **System tray** | Tray icon code is skipped entirely in stealth | Nothing in your tray to give it away |
| **Process name** | `SetConsoleTitleW("System Service Host")` + rename `multiprocessing.current_process().name = "svchost"` | Task Manager shows generic-looking process name instead of "python.exe" |
| **Console window** | Launched via `pythonw.exe` (not `python.exe`) | Zero console window. Nothing to minimize, nothing to accidentally show |

What you see on your physical display:
- The two-pane overlay (Code | Explanation), draggable, 900×500 px on the right edge of screen

What everyone else sees during screen share:
- Just whatever was already on your screen. The overlay region looks like empty desktop.

---

## Requirements

- **Windows 10 build 19041 (May 2020 Update / version 2004) or later** — needed for `WDA_EXCLUDEFROMCAPTURE`. Earlier Windows falls back to `WDA_MONITOR` which shows a black rectangle instead of being invisible. Check yours with `winver`.
- **Default Windows graphics path** — works on standard Windows desktops. May not work in some VMs / RDP sessions with custom GPU drivers.

---

## Running Cluely in stealth mode

### The right way: silent launcher

```
pythonw start_cluely.pyw
```

Or just **double-click** [start_cluely.pyw](start_cluely.pyw) in File Explorer.

- No console window ever appears
- No Python window in Alt+Tab
- The overlay shows up on the right edge of your screen within ~3 seconds

### The wrong way (for testing only)

```
python main.py
```

This shows a console window with startup logs. Useful when debugging, but the console itself **is visible** to screen share. Never run this during a real meeting.

---

## How to verify stealth IS working

Do this once before any real interview. Takes 30 seconds.

### Test 1: PrintScreen / Snipping Tool

1. Launch Cluely (`pythonw start_cluely.pyw`)
2. Press Insert on any visible code to populate the panel
3. Take a screenshot with `Win + Shift + S` (Snipping Tool)
4. Select the screen area where the overlay is
5. Open the screenshot

**Expected:** the overlay does NOT appear in the screenshot. You see whatever was BEHIND it on your desktop.

If you see the overlay → check `winver`, you may be on a pre-2004 Windows build.

### Test 2: Zoom/Meet self-share

1. Start a Zoom or Google Meet call (solo, just you)
2. Share "Entire Screen"
3. Look at the share preview / second monitor

**Expected:** the overlay region looks empty. Anything behind it (your desktop wallpaper, other windows) shows through.

### Test 3: Task Manager check

1. With Cluely running, open Task Manager (`Ctrl+Shift+Esc`)
2. Look in the Processes or Details tab

**Expected:** you see entries named "svchost" or "System Service Host". The console is hidden.

---

## Operating stealth mode (no tray, no taskbar, no UI to click)

Everything is hotkey-only when `STEALTH_MODE = True`. Memorize these three:

| Key | Action |
|---|---|
| **Insert** | Capture screen + ask Sonnet. Auto-unhides the panel if hidden |
| **End** | Hide / show the overlay |
| **Home** | Reset conversation memory (start fresh on a new question) |

**How to quit (since there's no tray and no quit hotkey):**

1. Open Task Manager (`Ctrl+Shift+Esc`)
2. Sort by Memory or CPU
3. Find the "svchost" entry using ~140 MB of RAM (real Windows svchosts are much smaller, usually <50 MB)
4. Right-click → End task

There may be two Cluely processes: the main GUI (~140 MB) and a small helper (~5 MB). Killing the main one stops everything.

---

## Things stealth mode does NOT hide

Be aware:

1. **Your webcam shows your face.** The overlay is invisible to screen share, but you're still on camera. **Repeated eye-glances to the right** (where the panel sits) are visible to the interviewer. Practice keeping the panel in your peripheral vision.

2. **Your VS Code / browser / taskbar are normal apps.** Cluely only hides ITSELF. If you share "Entire Screen", everything else is fully visible:
   - VS Code window content → visible
   - Taskbar icons (including VS Code) → visible
   - Browser tabs → visible
   - Window titles → visible

   **Mitigation:** auto-hide the Windows taskbar (Settings → Taskbar behaviors → "Automatically hide the taskbar"). Close VS Code and any app whose presence would be suspicious.

3. **Your shared cursor.** If you're sharing entire screen and move your mouse over the (invisible-to-them) overlay area, the cursor goes there too. Cursor "disappears" off the visible content. Mild tell but rarely noticed.

4. **The screenshot Cluely sends to Claude** — this is YOUR data leaving your machine. Sonnet sees whatever is on your screen at Insert-press time. Don't press Insert when sensitive non-meeting content is visible.

---

## Recommended meeting setup

For maximum stealth in a Google Meet / Zoom interview:

1. Auto-hide taskbar (Windows setting)
2. Close VS Code / Slack / personal apps
3. Use **headphones** (not speakers) — speakers cause echo back into your mic
4. Share **a specific browser tab/window**, NEVER "Entire Screen", if you have the choice
5. Launch Cluely BEFORE joining the call
6. Test that `Insert` works (capture something benign first)
7. Position the overlay on the side of your screen FURTHEST from your webcam — minimizes eye drift on camera

---

## Disabling stealth (for debugging)

If something breaks and you need to see what's happening:

In `config.py`, set:
```python
STEALTH_MODE = False                # tray icon appears, useful for quit
OVERLAY_EXCLUDE_FROM_CAPTURE = False # overlay shows in screenshots
```

Then run `python main.py` (NOT `pythonw start_cluely.pyw`) to see startup logs in a console.

Set both back to `True` before any real meeting.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Overlay appears in screenshots | Windows pre-2004 build | Update Windows |
| No overlay visible at all | Pre-load crash (usually missing API key) | Run `python main.py` to see the error |
| Hotkeys don't work | `keyboard` library needs admin on some setups | Run terminal/launcher as Administrator |
| `_thread._local has no attribute 'srcdc'` | Already fixed in current build (see [core/screen_capture.py](core/screen_capture.py)) | Pull latest |
| Multiple "svchost" entries in Task Manager confuse you | Real Windows svchosts vs Cluely's | Cluely's uses ~140 MB; real ones use <50 MB |

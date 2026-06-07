# Cluely - User Manual

## Quick Start (30 seconds)

```bash
cd C:\Users\bhush\Desktop\cluely
venv\Scripts\activate
python main.py
```

That's it. The overlay appears on the right side of your screen. Press `Ctrl+Shift+S` to start listening.

---

## How It Works

### Two Modes

| Mode | How it works | When to use |
|------|-------------|-------------|
| **AUTO (default)** | Claude responds automatically after every speech chunk. You don't press anything. | During meetings/interviews - hands-free |
| **MANUAL** | You press `Ctrl+Shift+A` when you want Claude's help. | When you want control over when AI responds |

Change mode in `config.py`:
```python
AUTO_RESPONSE = True    # True = autonomous, False = manual
```

### The Pipeline (What Happens Automatically)

```
1. Someone speaks in meeting
2. WASAPI captures audio from your speakers (every 5 seconds)
3. Whisper transcribes speech to text (~1 second on your CPU)
4. Transcript appears in the overlay
5. [AUTO MODE] Claude reads transcript and generates a response
6. Response appears in the overlay's green "AI ASSISTANT" section
7. You read it and use it however you want
```

**Total delay: ~1.5 seconds** from speech to AI suggestion on your system.

---

## Hotkeys

| Hotkey | Action | When to use |
|--------|--------|-------------|
| `Ctrl+Shift+S` | **Start/Stop listening** | Beginning and end of a meeting |
| `Ctrl+Shift+H` | **Hide/Show overlay** | When you need to temporarily hide/show the panel |
| `Ctrl+Shift+A` | **Ask Claude** | In manual mode, or when you want an extra response in auto mode |
| `Ctrl+Shift+P` | **Screenshot + AI** | When there's something visual on screen (code, slides, diagrams) |
| `Ctrl+Shift+N` | **Generate meeting notes** | At the end of a meeting to get a summary |
| `Ctrl+Shift+Q` | **Quit Cluely** | When you're done |

All hotkeys are changeable in `config.py` under the `HOTKEYS` section.

---

## The Overlay

```
┌─────────────────────────┐
│ CLUELY    Auto|Listening│  ← Status bar (draggable)
├─────────────────────────┤
│ TRANSCRIPT              │
│ [Speaker] Hello, can    │  ← What others are saying
│ you tell me about your  │
│ experience with Python? │
├─────────────────────────┤
│ AI ASSISTANT            │
│ • You have 3 years of   │  ← Claude's suggestions
│   Python experience     │
│ • Mention Django project│
│ • Talk about async/await│
├─────────────────────────┤
│ [Start] [Ask AI] [Screen]│  ← Buttons (also work)
└─────────────────────────┘
```

- **Drag** the overlay by clicking and dragging the title bar
- **Resize** using the grip at the bottom-right corner
- **Position**: Change in config.py → `OVERLAY_POSITION = "right"` (or "left" / "bottom")
- **Opacity**: Change → `OVERLAY_OPACITY = 0.85` (0.0 to 1.0)

### Stealth Mode
The overlay is **completely invisible** to:
- Zoom screen share
- Google Meet screen share
- Microsoft Teams screen share
- OBS recording
- Windows screenshot (PrintScreen, Snipping Tool)

It only appears on your physical display. Others cannot see it.

---

## System Tray

Right-click the circle icon in your system tray (bottom-right of taskbar) for:
- Start/Stop Listening
- Toggle Overlay
- Ask AI
- Screenshot
- Generate Notes
- Quit

---

## What Gets Saved

When you stop listening (`Ctrl+Shift+S` again), Cluely automatically saves:

| File | Location | Content |
|------|----------|---------|
| Transcript | `sessions/session_YYYYMMDD_HHMMSS_transcript.txt` | Full timestamped transcript |
| Meeting Notes | `sessions/session_YYYYMMDD_HHMMSS_notes.md` | AI summary + action items (when you press Ctrl+Shift+N) |
| Email Draft | `sessions/email_draft_YYYYMMDD_HHMMSS.md` | Auto-generated follow-up email |

---

## Testing Guide

### Test 1: YouTube Interview Video (Easiest - Do This First)

1. Open YouTube in your browser
2. Search for "mock technical interview" or "job interview example"
3. Start playing the video with audio through your **speakers** (not headphones initially)
4. Run `python main.py`
5. Press `Ctrl+Shift+S` to start listening
6. Watch the TRANSCRIPT section fill up with what's being said
7. In AUTO mode, Claude will start suggesting responses automatically
8. Press `Ctrl+Shift+N` to generate notes from what was captured

**Why this works**: WASAPI loopback captures whatever audio plays through your speakers. YouTube audio → speakers → Cluely captures it.

### Test 2: Stealth Verification

1. With Cluely overlay visible, press `Win+Shift+S` (Windows snip)
2. Take a screenshot of the area where the overlay is
3. Check the screenshot → the overlay should NOT appear in it
4. Try screen sharing on any platform → overlay stays invisible

### Test 3: Screenshot + AI

1. Open something interesting on screen (code, document, slide)
2. Press `Ctrl+Shift+P`
3. Cluely captures your screen and sends it to Claude along with the transcript
4. Claude responds with visual + audio context combined

### Test 4: With Headphones

If you use headphones/earbuds during meetings (Kartik's Buds3 Pro), WASAPI will capture audio from whatever your default output device is. Just make sure your meeting audio plays through the device Cluely is capturing.

### Test 5: Real Zoom/Meet Call (When Ready)

1. Start `python main.py`
2. Join a Zoom or Google Meet call
3. Press `Ctrl+Shift+S` to start listening
4. The meeting audio gets captured → transcribed → Claude responds
5. Share your screen → verify overlay is NOT visible to others
6. Press `Ctrl+Shift+N` at the end for meeting notes

---

## Troubleshooting

### "No audio captured"
- Make sure audio is playing through your **default speakers** (device [8])
- Check: `python tools/latency_test.py --devices` to see your audio devices
- Try setting `AUDIO_DEVICE = 8` in config.py explicitly

### "Hotkeys not working"
- Install: `pip install keyboard pynput`
- Try running terminal as **Administrator** (keyboard library sometimes needs this)
- Alternative: Use the **overlay buttons** or **system tray menu** instead

### "Transcript is empty but audio is playing"
- Audio might be too quiet → lower `SILENCE_THRESHOLD = 0.005` in config.py
- Check WASAPI device → set `AUDIO_DEVICE = 8` in config.py

### "Claude responses are slow"
- Normal: ~1.5s with your setup
- For faster: switch to Deepgram → set `STT_PROVIDER = "deepgram"` in config.py
- For lighter responses: lower `CLAUDE_MAX_TOKENS = 512`

---

## Config Quick Reference

Edit `config.py` to customize. Key settings:

```python
# Switch to autonomous or manual
AUTO_RESPONSE = True              # True = auto, False = press Ctrl+Shift+A

# Change AI model (Haiku = fastest, Sonnet = smarter)
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# Audio chunk size (smaller = more frequent responses, higher API cost)
AUDIO_CHUNK_DURATION = 5          # seconds

# Switch STT provider
STT_PROVIDER = "whisper"          # "whisper" (free) or "deepgram" (fast)

# Overlay appearance
OVERLAY_OPACITY = 0.85
OVERLAY_POSITION = "right"        # "left", "right", "bottom"
OVERLAY_WIDTH = 420
OVERLAY_HEIGHT = 600
```

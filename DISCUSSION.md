# Cluely - Project Discussion & Architecture Notes

## What We're Building
A personal real-time AI meeting assistant that runs as an **invisible desktop overlay** during online meetings/interviews. It captures audio, transcribes in real-time, and uses Claude API to generate context-aware responses, suggestions, and meeting notes.

---

## Key Decisions Made

### Hardware Context
- **CPU**: AMD Ryzen 7000 series laptop
- **GPU**: AMD Radeon integrated graphics (no NVIDIA)
- **Implication**: No CUDA → Whisper runs on CPU only → `base` model recommended

### Tech Stack
| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.11+ | Best ecosystem for audio/AI/Windows APIs |
| UI | PyQt6 | Native transparent overlay + system tray |
| Audio Capture | sounddevice (WASAPI loopback) | Captures system audio without virtual cables |
| STT (default) | faster-whisper (local) | Free, no API costs, ~2-4s latency on CPU |
| STT (alternative) | Deepgram (cloud) | <500ms latency, costs ~$0.006/min |
| AI Model | Claude Haiku 4.5 (streaming) | Fastest Claude model, ~500ms to first token |
| Screenshots | mss | Fast screen capture, hotkey-triggered |
| Stealth | SetWindowDisplayAffinity | Windows API to hide overlay from screen capture |

### STT Architecture: Modular Design
- Abstract base class `TranscriberBase`
- Swap between Whisper and Deepgram by changing ONE line in `config.py`
- Factory pattern: `create_transcriber(provider)` returns the right implementation
- Latency test tool to benchmark both providers on your hardware

### Screen Capture Exclusion
- Uses `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` (Windows 10 2004+)
- Makes overlay **invisible** to: Zoom share, Meet share, Teams share, OBS, PrintScreen
- Window remains visible on physical display only

---

## What is WASAPI Audio?
**WASAPI** = Windows Audio Session API

Windows' low-level audio interface. We use **loopback mode** which:
- Captures exactly what plays through speakers/headphones
- No virtual audio cable or Stereo Mix needed
- Low latency, direct buffer access
- Can target specific audio output devices

**Flow**: Meeting app → audio to speakers → WASAPI loopback intercepts copy → fed to STT

---

## Architecture Overview

### Data Flow
```
[Meeting Audio via Speakers]
        ↓
   WASAPI Loopback (captures system audio)
        ↓
   Audio Chunks (5 seconds each, 16kHz, mono)
        ↓
   STT Engine (Whisper local OR Deepgram cloud)
        ↓
   Transcript Text
        ↓
   Claude Haiku 4.5 (streaming response)
        ↓
   Overlay UI (invisible to screen capture)
```

### Project Structure
```
cluely/
├── main.py                    # Entry point
├── config.py                  # ALL settings in one place
├── requirements.txt           # Dependencies
├── core/
│   ├── audio_capture.py       # WASAPI loopback + mic capture
│   ├── transcriber_base.py    # Abstract STT interface
│   ├── whisper_stt.py         # Local Whisper implementation
│   ├── deepgram_stt.py        # Cloud Deepgram implementation
│   ├── ai_engine.py           # Claude API with streaming
│   ├── screen_capture.py      # Screenshot capture
│   └── session.py             # Session management & export
├── ui/
│   ├── overlay.py             # Transparent stealth overlay
│   ├── system_tray.py         # System tray icon & menu
│   └── styles.py              # Dark theme styling
├── utils/
│   ├── hotkeys.py             # Global hotkey management
│   └── windows_api.py         # Windows-specific APIs
├── tools/
│   ├── install_whisper.py     # Download & verify Whisper model
│   └── latency_test.py        # Benchmark STT providers
└── sessions/                  # Saved transcripts & notes
```

---

## Hotkey Bindings (Configurable)
| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+S` | Start/Stop listening |
| `Ctrl+Shift+H` | Hide/Show overlay |
| `Ctrl+Shift+A` | Ask Claude (AI response from transcript) |
| `Ctrl+Shift+P` | Capture screenshot + send to Claude |
| `Ctrl+Shift+N` | Generate meeting notes/summary |
| `Ctrl+Shift+Q` | Quit application |

---

## Configuration Defaults
```python
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
STT_PROVIDER = "whisper"          # "whisper" or "deepgram"
WHISPER_MODEL_SIZE = "base"       # tiny/base/small/medium
AUDIO_SAMPLE_RATE = 16000         # Hz
AUDIO_CHUNK_DURATION = 5          # seconds per chunk
OVERLAY_OPACITY = 0.85            # 0.0 to 1.0
OVERLAY_POSITION = "right"        # left/right/bottom
```

---

## Performance Expectations (Ryzen 7000 CPU)
| Component | Latency |
|-----------|---------|
| Whisper `tiny` | ~1-2s per 5s chunk |
| Whisper `base` | ~2-4s per 5s chunk |
| Deepgram cloud | <500ms streaming |
| Claude Haiku 4.5 | ~500ms to first token |
| **Total (Whisper)** | **~3-7s speech to suggestion** |
| **Total (Deepgram)** | **~1-3s speech to suggestion** |

---

## Future Discussion Topics
- [ ] Deep dive: How conversation audio is captured chunk by chunk
- [ ] API call optimization: batching, context windows, cost control
- [ ] Fine-tuning AUDIO_SAMPLE_RATE and AUDIO_CHUNK_DURATION
- [ ] Overlay UX improvements: position, opacity, click-through
- [ ] Session export formats and post-meeting summaries
- [ ] Testing on real Zoom/Meet/Teams calls

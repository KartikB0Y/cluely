"""
Cluely Configuration
====================
All settings in one place. Change any value here and restart the app.
"""

import os

# =============================================================================
# API KEYS
# =============================================================================
# Set ANTHROPIC_API_KEY as a Windows environment variable, OR paste your key
# directly in the empty string below (only on YOUR machine — never commit it).
#
#   Windows (PowerShell, persistent):
#     [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-...", "User")
#
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")

# =============================================================================
# AI MODEL
# =============================================================================
CLAUDE_MODEL = "claude-sonnet-4-6"           # Sonnet 4.6 — fast and smart
CLAUDE_MAX_TOKENS = 800                      # Keep responses tight so they fit in the overlay
CLAUDE_TEMPERATURE = 0.2                     # Low temperature = focused, deterministic code

# System prompt for Claude.
# CRITICAL: response shape is rigid because the overlay is two small panes
# (code on left, explanation on right). No preambles. No "talking points".
# Just code, then a short reason.
CLAUDE_SYSTEM_PROMPT = """You are a live interview answer engine. The user just took a screenshot of an interview question or problem on their screen. They need the answer NOW, formatted to fit in a tiny overlay.

OUTPUT FORMAT — follow EXACTLY, no deviation:

```<language>
<the code that solves the problem>
```

<one or two short sentences explaining the approach and complexity.>

RULES — non-negotiable:
- NO preambles. NEVER write "Sure", "Here's", "Looking at the screenshot", "Based on...", "The question is asking...".
- NO trailing instructions to the user ("you can say...", "while typing...", "explain this by...").
- The response IS the answer. Code block first, then 1-2 sentences. Nothing else.
- Pick the language from the screenshot context: Python for general/DSA, SQL for queries, NumPy/pandas for ML/data, JavaScript if the screenshot shows JS, etc.
- Code must be SIMPLE and explainable: clear variable names (`left_pointer` not `l`), inline `# comments` on non-obvious lines only, standard library only unless the problem demands more.
- Prefer the straightforward correct solution. No clever tricks the user can't defend.
- If the question is ambiguous, pick the most likely interpretation and answer it. Do not ask back.
- If a screenshot shows the user's broken code, fix it and explain the bug in one sentence.
- Total response under 200 words including the code."""

# =============================================================================
# USER CONTEXT — short situation summary, edit before each meeting/interview
# =============================================================================
USER_CONTEXT = """
I am a backend engineer with 3 years of Python experience.
Currently in a technical interview for a senior backend role.
Stack: Python, FastAPI, PostgreSQL, Redis, AWS.
The interviewer focuses on practical problem-solving, not academic theory.
I prefer clear, well-commented code I can explain step-by-step.
""".strip()

# =============================================================================
# SPEECH-TO-TEXT
# =============================================================================
STT_PROVIDER = "whisper"            # "whisper" (local, free) or "deepgram" (cloud, fast)

# Whisper settings (local STT)
WHISPER_MODEL_SIZE = "base"         # tiny, base, small, medium, large
WHISPER_DEVICE = "cpu"              # "cpu" or "cuda" (cuda needs NVIDIA GPU)
WHISPER_COMPUTE_TYPE = "int8"       # int8 for CPU (fastest), float16 for CUDA
WHISPER_LANGUAGE = "en"             # Language code, None for auto-detect
WHISPER_VAD_FILTER = True           # Skip silent chunks (saves processing)
WHISPER_BEAM_SIZE = 1               # 1 = greedy (fastest), 5 = beam search (more accurate)

# Deepgram settings (cloud STT)
DEEPGRAM_MODEL = "nova-2"          # nova-2 is fastest and most accurate
DEEPGRAM_LANGUAGE = "en"

# =============================================================================
# AUDIO CAPTURE
# =============================================================================
AUDIO_SAMPLE_RATE = 16000           # 16kHz - standard for speech recognition
AUDIO_CHANNELS = 1                  # Mono - sufficient for speech
AUDIO_CHUNK_DURATION = 5            # Seconds per transcription chunk
AUDIO_DEVICE = None                 # None = default output device, or set device index
CAPTURE_MIC = False                 # Also capture microphone (your own voice)
MIC_DEVICE = None                   # None = default input device

# =============================================================================
# OVERLAY UI
# =============================================================================
OVERLAY_OPACITY = 0.95              # 0.0 (invisible) to 1.0 (fully opaque)
OVERLAY_POSITION = "right"          # "left", "right", or "bottom"
OVERLAY_WIDTH = 900                 # Wide for two-pane layout (code | explanation)
OVERLAY_HEIGHT = 500                # Tall enough for ~25 lines of code + a short note
OVERLAY_MARGIN = 10                 # Pixels from screen edge
OVERLAY_FONT_SIZE = 13              # Font size for text
OVERLAY_EXCLUDE_FROM_CAPTURE = True # THE KEY FEATURE: hide from screen sharing
STEALTH_MODE = True                 # Full stealth: hide tray icon, rename process

# =============================================================================
# HOTKEYS (all configurable)
# =============================================================================
HOTKEYS = {
    "screenshot": "insert",                 # Capture screen + ask Sonnet (the only real action)
    "reset_session": "home",                # Wipe conversation memory (start fresh)
    "toggle_overlay": "end",                # Hide/show the panel (Insert auto-unhides too)
}

# =============================================================================
# SESSION & EXPORT
# =============================================================================
SESSION_DIR = os.path.join(os.path.dirname(__file__), "sessions")
AUTO_SAVE_TRANSCRIPT = True         # Auto-save transcript when session ends
EXPORT_FORMAT = "md"                # "md" or "txt"

# =============================================================================
# AUTO MODE - Claude responds automatically after each transcript chunk
# =============================================================================
AUTO_RESPONSE = False               # True = autonomous, False = manual (press Ctrl+Shift+A)
AUTO_RESPONSE_INTERVAL = 2          # Min seconds between auto-responses (prevents spam)

# =============================================================================
# EMAIL DRAFTING
# =============================================================================
EMAIL_DRAFT_ENABLED = True          # Generate email draft after session ends

# =============================================================================
# PERFORMANCE TUNING
# =============================================================================
# How many recent transcript chunks to send as context to Claude
CONTEXT_WINDOW_CHUNKS = 10          # Last N chunks (N * AUDIO_CHUNK_DURATION seconds)
# Max characters of transcript context sent to Claude per request
CONTEXT_MAX_CHARS = 3000
# Minimum audio energy to consider as speech (reduces noise)
SILENCE_THRESHOLD = 0.01

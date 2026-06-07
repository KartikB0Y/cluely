"""
Session Manager
===============
Manages the meeting session lifecycle: transcript accumulation,
AI responses, timestamps, and export.
"""

import os
import time
from datetime import datetime


class Session:
    """Tracks a single meeting session with transcript and AI responses."""

    def __init__(self):
        from config import SESSION_DIR, CONTEXT_WINDOW_CHUNKS, CONTEXT_MAX_CHARS

        self.session_dir = SESSION_DIR
        self.context_window = CONTEXT_WINDOW_CHUNKS
        self.context_max_chars = CONTEXT_MAX_CHARS

        self.start_time = None
        self.transcript_chunks = []     # List of (timestamp, source, text)
        self.ai_responses = []          # List of (timestamp, response)
        self.is_active = False

        # Ensure session directory exists
        os.makedirs(self.session_dir, exist_ok=True)

    def start(self):
        """Start a new session."""
        self.start_time = datetime.now()
        self.transcript_chunks = []
        self.ai_responses = []
        self.is_active = True
        print(f"[session] Session started at {self.start_time.strftime('%H:%M:%S')}")

    def stop(self):
        """Stop the current session."""
        self.is_active = False
        duration = self._get_duration()
        print(f"[session] Session stopped. Duration: {duration}")

    def add_transcript(self, text: str, source: str = "system"):
        """
        Add a transcript chunk.

        Args:
            text: Transcribed text
            source: "system" (others' audio) or "mic" (your audio)
        """
        if not text.strip():
            return
        timestamp = datetime.now()
        self.transcript_chunks.append((timestamp, source, text.strip()))

    def add_ai_response(self, response: str):
        """Add an AI response to the session log."""
        timestamp = datetime.now()
        self.ai_responses.append((timestamp, response))

    def get_recent_context(self) -> str:
        """
        Get recent transcript text for Claude context.
        Returns the last N chunks as a single string.
        """
        recent = self.transcript_chunks[-self.context_window:]
        lines = []
        for ts, source, text in recent:
            prefix = "[You]" if source == "mic" else "[Other]"
            lines.append(f"{prefix} {text}")

        context = "\n".join(lines)
        # Trim to max chars
        if len(context) > self.context_max_chars:
            context = context[-self.context_max_chars:]
        return context

    def get_full_transcript(self) -> str:
        """Get the complete transcript as a formatted string."""
        lines = []
        for ts, source, text in self.transcript_chunks:
            time_str = ts.strftime("%H:%M:%S")
            prefix = "[You]" if source == "mic" else "[Speaker]"
            lines.append(f"[{time_str}] {prefix} {text}")
        return "\n".join(lines)

    def _get_duration(self) -> str:
        """Get session duration as formatted string."""
        if not self.start_time:
            return "0:00"
        delta = datetime.now() - self.start_time
        minutes = int(delta.total_seconds() // 60)
        seconds = int(delta.total_seconds() % 60)
        return f"{minutes}:{seconds:02d}"

    def _get_filename_base(self) -> str:
        """Generate a filename base from session start time."""
        if self.start_time:
            return self.start_time.strftime("session_%Y%m%d_%H%M%S")
        return f"session_{int(time.time())}"

    def save_transcript(self) -> str:
        """
        Save the full transcript to a file.

        Returns:
            Path to saved file
        """
        filename = self._get_filename_base() + "_transcript.txt"
        filepath = os.path.join(self.session_dir, filename)

        content = f"Meeting Transcript\n"
        content += f"Date: {self.start_time.strftime('%Y-%m-%d %H:%M')}\n"
        content += f"Duration: {self._get_duration()}\n"
        content += f"{'='*60}\n\n"
        content += self.get_full_transcript()

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[session] Transcript saved: {filepath}")
        return filepath

    def save_notes(self, summary: str) -> str:
        """
        Save meeting notes (summary + transcript) as markdown.

        Args:
            summary: AI-generated summary text

        Returns:
            Path to saved file
        """
        filename = self._get_filename_base() + "_notes.md"
        filepath = os.path.join(self.session_dir, filename)

        content = f"# Meeting Notes\n\n"
        content += f"**Date**: {self.start_time.strftime('%Y-%m-%d %H:%M')}\n"
        content += f"**Duration**: {self._get_duration()}\n\n"
        content += f"---\n\n"
        content += f"{summary}\n\n"
        content += f"---\n\n"
        content += f"## Full Transcript\n\n"
        content += f"```\n{self.get_full_transcript()}\n```\n"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[session] Notes saved: {filepath}")
        return filepath

    def get_stats(self) -> dict:
        """Get session statistics."""
        return {
            "duration": self._get_duration(),
            "total_chunks": len(self.transcript_chunks),
            "system_chunks": sum(1 for _, s, _ in self.transcript_chunks if s == "system"),
            "mic_chunks": sum(1 for _, s, _ in self.transcript_chunks if s == "mic"),
            "ai_responses": len(self.ai_responses),
            "total_words": sum(len(t.split()) for _, _, t in self.transcript_chunks),
        }

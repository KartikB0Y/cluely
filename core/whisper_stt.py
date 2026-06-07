"""
Whisper STT (Local Speech-to-Text)
==================================
Uses faster-whisper with CTranslate2 for CPU-optimized transcription.
Free, runs locally, no API costs.
"""

import numpy as np
from core.transcriber_base import TranscriberBase


class WhisperTranscriber(TranscriberBase):
    """Local Whisper-based speech-to-text using faster-whisper."""

    def __init__(self):
        from config import (
            WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE,
            WHISPER_LANGUAGE, WHISPER_VAD_FILTER, WHISPER_BEAM_SIZE
        )
        self.model_size = WHISPER_MODEL_SIZE
        self.device = WHISPER_DEVICE
        self.compute_type = WHISPER_COMPUTE_TYPE
        self.language = WHISPER_LANGUAGE
        self.vad_filter = WHISPER_VAD_FILTER
        self.beam_size = WHISPER_BEAM_SIZE
        self._model = None

    def _load_model(self):
        """Lazy-load the model on first use."""
        if self._model is None:
            from faster_whisper import WhisperModel
            print(f"[whisper_stt] Loading model '{self.model_size}' on {self.device}...")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            print(f"[whisper_stt] Model loaded successfully.")

    def warmup(self):
        """
        Force-load the model and run a dummy transcription.
        Call this at startup so the model is hot when real audio arrives.
        """
        self._load_model()
        # Run a tiny dummy transcription to warm up all internal buffers
        dummy = np.zeros(16000, dtype=np.float32)  # 1 second of silence
        segments, _ = self._model.transcribe(dummy, beam_size=1, language=self.language)
        # Consume the generator to force execution
        for _ in segments:
            pass
        print(f"[whisper_stt] Model warmed up and ready.")

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio using local Whisper model.

        Args:
            audio_data: float32 numpy array of audio samples
            sample_rate: sample rate (must be 16000 for Whisper)

        Returns:
            Transcribed text
        """
        self._load_model()

        # Ensure correct dtype
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Ensure 1D
        if audio_data.ndim > 1:
            audio_data = audio_data.flatten()

        segments, info = self._model.transcribe(
            audio_data,
            beam_size=self.beam_size,
            language=self.language,
            vad_filter=self.vad_filter,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=300,
            ),
        )

        # Collect all segment texts
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        return " ".join(text_parts)

    def get_name(self) -> str:
        return f"Whisper ({self.model_size}, {self.device})"

    def get_latency_estimate(self) -> float:
        estimates = {
            "tiny": 1.5,
            "base": 3.0,
            "small": 7.0,
            "medium": 20.0,
            "large": 45.0,
        }
        return estimates.get(self.model_size, 5.0)

    def is_available(self) -> bool:
        try:
            import faster_whisper
            return True
        except ImportError:
            return False

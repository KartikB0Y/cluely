"""
Transcriber Base Interface
==========================
Abstract base class for all STT (Speech-to-Text) providers.
Swap providers by changing STT_PROVIDER in config.py.
"""

from abc import ABC, abstractmethod
import numpy as np


class TranscriberBase(ABC):
    """Abstract base class for speech-to-text providers."""

    @abstractmethod
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio data to text.

        Args:
            audio_data: numpy array of float32 audio samples
            sample_rate: audio sample rate in Hz

        Returns:
            Transcribed text string
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this STT provider."""
        pass

    @abstractmethod
    def get_latency_estimate(self) -> float:
        """Return estimated latency in seconds for a 5s audio chunk."""
        pass

    def is_available(self) -> bool:
        """Check if this provider is ready to use."""
        return True


def create_transcriber(provider: str = None) -> TranscriberBase:
    """
    Factory function to create the appropriate transcriber.

    Args:
        provider: "whisper" or "deepgram". None = read from config.

    Returns:
        TranscriberBase instance
    """
    if provider is None:
        from config import STT_PROVIDER
        provider = STT_PROVIDER

    if provider == "whisper":
        from core.whisper_stt import WhisperTranscriber
        return WhisperTranscriber()
    elif provider == "deepgram":
        from core.deepgram_stt import DeepgramTranscriber
        return DeepgramTranscriber()
    else:
        raise ValueError(f"Unknown STT provider: '{provider}'. Use 'whisper' or 'deepgram'.")

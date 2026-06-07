"""
Deepgram STT (Cloud Speech-to-Text)
====================================
Uses Deepgram's Nova-2 model for ultra-low latency cloud transcription.
Requires DEEPGRAM_API_KEY in config.py.
Cost: ~$0.0059/minute.
"""

import numpy as np
from core.transcriber_base import TranscriberBase


class DeepgramTranscriber(TranscriberBase):
    """Deepgram cloud-based speech-to-text."""

    def __init__(self):
        from config import DEEPGRAM_API_KEY, DEEPGRAM_MODEL, DEEPGRAM_LANGUAGE
        self.api_key = DEEPGRAM_API_KEY
        self.model = DEEPGRAM_MODEL
        self.language = DEEPGRAM_LANGUAGE
        self._client = None

    def _get_client(self):
        """Lazy-init the Deepgram client."""
        if self._client is None:
            from deepgram import DeepgramClient
            self._client = DeepgramClient(self.api_key)
        return self._client

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio using Deepgram cloud API.

        Args:
            audio_data: float32 numpy array of audio samples
            sample_rate: sample rate in Hz

        Returns:
            Transcribed text
        """
        from deepgram import PrerecordedOptions

        client = self._get_client()

        # Convert float32 to int16 bytes for Deepgram
        if audio_data.dtype == np.float32:
            audio_int16 = (audio_data * 32767).astype(np.int16)
        else:
            audio_int16 = audio_data.astype(np.int16)

        audio_bytes = audio_int16.tobytes()

        response = client.listen.rest.v("1").transcribe_file(
            {"buffer": audio_bytes, "mimetype": "audio/raw"},
            PrerecordedOptions(
                model=self.model,
                language=self.language,
                encoding="linear16",
                sample_rate=sample_rate,
                channels=1,
                smart_format=True,
            ),
        )

        transcript = response.results.channels[0].alternatives[0].transcript
        return transcript.strip()

    def get_name(self) -> str:
        return f"Deepgram ({self.model})"

    def get_latency_estimate(self) -> float:
        return 0.5  # ~500ms typical

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            import deepgram
            return True
        except ImportError:
            return False

"""
Audio Capture Module
====================
Captures system audio via WASAPI loopback using PyAudioWPatch.
Optionally captures microphone audio.
Runs in background threads and delivers audio chunks via callback.

PyAudioWPatch provides reliable WASAPI loopback on Windows —
captures exactly what plays through speakers/headphones.
Audio is captured at the device's native sample rate (usually 48kHz)
and resampled to 16kHz for Whisper.
"""

import threading
import queue
import time
import numpy as np


class AudioCapture:
    """
    Captures system audio via WASAPI loopback + optional mic.
    Delivers resampled 16kHz mono audio chunks to a callback.
    """

    def __init__(self, on_audio_chunk=None):
        from config import (
            AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_DURATION,
            AUDIO_DEVICE, CAPTURE_MIC, MIC_DEVICE, SILENCE_THRESHOLD
        )
        self.target_sample_rate = AUDIO_SAMPLE_RATE  # 16000 for Whisper
        self.channels = AUDIO_CHANNELS
        self.chunk_duration = AUDIO_CHUNK_DURATION
        self.system_device = AUDIO_DEVICE
        self.capture_mic = CAPTURE_MIC
        self.mic_device = MIC_DEVICE
        self.silence_threshold = SILENCE_THRESHOLD

        self.on_audio_chunk = on_audio_chunk
        self._running = False
        self._system_thread = None
        self._mic_thread = None
        self._dispatch_thread = None
        self._audio_queue = queue.Queue()

    def _find_loopback_device(self, p):
        """
        Find the WASAPI loopback device for system audio capture.
        PyAudioWPatch exposes loopback devices with isLoopbackDevice=True.
        """
        import pyaudiowpatch as pyaudio

        # If user specified a device index, use it
        if self.system_device is not None:
            return p.get_device_info_by_index(self.system_device)

        # Get WASAPI host API
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            raise RuntimeError("WASAPI not available on this system!")

        # Get default output device
        default_output_idx = wasapi_info["defaultOutputDevice"]
        default_speakers = p.get_device_info_by_index(default_output_idx)
        speaker_name_prefix = default_speakers['name'].split('(')[0].strip()

        # Find matching loopback device
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev.get("isLoopbackDevice", False):
                if dev['name'].startswith(speaker_name_prefix):
                    return dev

        # Fallback: any loopback device
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev.get("isLoopbackDevice", False):
                return dev

        raise RuntimeError(
            "No WASAPI loopback device found! "
            "Make sure you have audio output devices available."
        )

    def _resample_to_16k(self, audio, source_rate):
        """
        Resample audio from source_rate to 16kHz for Whisper.
        Uses simple decimation — fast, no scipy dependency.
        48000 / 16000 = 3, so we take every 3rd sample.
        For non-integer ratios, uses linear interpolation.
        """
        if source_rate == self.target_sample_rate:
            return audio

        ratio = source_rate / self.target_sample_rate

        # Integer ratio (e.g., 48000/16000 = 3) — simple decimation
        if ratio == int(ratio):
            step = int(ratio)
            # Simple low-pass: average adjacent samples before decimating
            # This prevents aliasing artifacts
            kernel_size = step
            if len(audio) >= kernel_size:
                # Pad to make length divisible
                pad_len = (kernel_size - len(audio) % kernel_size) % kernel_size
                if pad_len > 0:
                    audio = np.concatenate([audio, np.zeros(pad_len, dtype=np.float32)])
                # Reshape and average for anti-aliasing
                reshaped = audio[:len(audio) // kernel_size * kernel_size].reshape(-1, kernel_size)
                return reshaped.mean(axis=1).astype(np.float32)
            else:
                return audio[::step].astype(np.float32)
        else:
            # Non-integer ratio — linear interpolation
            target_len = int(len(audio) * self.target_sample_rate / source_rate)
            indices = np.linspace(0, len(audio) - 1, target_len)
            return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _capture_system_audio(self):
        """Background thread: capture system audio via WASAPI loopback."""
        import pyaudiowpatch as pyaudio

        p = pyaudio.PyAudio()

        try:
            loopback_dev = self._find_loopback_device(p)
            native_sr = int(loopback_dev['defaultSampleRate'])
            dev_channels = loopback_dev['maxInputChannels']
            dev_index = loopback_dev['index']

            print(f"[audio] System device: [{dev_index}] {loopback_dev['name']}")
            print(f"[audio] Native: {native_sr}Hz, {dev_channels}ch -> Resample to {self.target_sample_rate}Hz mono")

            CHUNK = 1024
            chunk_samples_native = int(native_sr * self.chunk_duration)
            buffer = np.zeros(0, dtype=np.float32)

            stream = p.open(
                format=pyaudio.paFloat32,
                channels=dev_channels,
                rate=native_sr,
                input=True,
                input_device_index=dev_index,
                frames_per_buffer=CHUNK,
            )

            print(f"[audio] System audio capture STARTED (WASAPI loopback)")

            while self._running:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    audio = np.frombuffer(data, dtype=np.float32)

                    # Convert to mono
                    if dev_channels > 1:
                        mono = audio.reshape(-1, dev_channels)[:, 0]
                    else:
                        mono = audio

                    buffer = np.concatenate([buffer, mono])

                    # When we have enough for a chunk
                    while len(buffer) >= chunk_samples_native:
                        chunk_native = buffer[:chunk_samples_native].copy()
                        buffer = buffer[chunk_samples_native:]

                        # Check energy (skip silence)
                        energy = np.sqrt(np.mean(chunk_native ** 2))
                        if energy > self.silence_threshold:
                            # Resample to 16kHz for Whisper
                            chunk_16k = self._resample_to_16k(chunk_native, native_sr)
                            self._audio_queue.put(("system", chunk_16k))

                except IOError as e:
                    print(f"[audio] Read error: {e}")
                    continue

            stream.stop_stream()
            stream.close()

        except Exception as e:
            print(f"[audio] System audio ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            p.terminate()

    def _capture_mic_audio(self):
        """Background thread: capture microphone audio."""
        import pyaudiowpatch as pyaudio

        p = pyaudio.PyAudio()

        try:
            # Use default input device or specified device
            if self.mic_device is not None:
                mic_info = p.get_device_info_by_index(self.mic_device)
            else:
                mic_info = p.get_default_input_device_info()

            native_sr = int(mic_info['defaultSampleRate'])
            dev_channels = min(mic_info['maxInputChannels'], 1)  # mono
            dev_index = mic_info['index']

            print(f"[audio] Mic device: [{dev_index}] {mic_info['name']}")

            CHUNK = 1024
            chunk_samples_native = int(native_sr * self.chunk_duration)
            buffer = np.zeros(0, dtype=np.float32)

            stream = p.open(
                format=pyaudio.paFloat32,
                channels=dev_channels,
                rate=native_sr,
                input=True,
                input_device_index=dev_index,
                frames_per_buffer=CHUNK,
            )

            print(f"[audio] Mic capture STARTED")

            while self._running:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    audio = np.frombuffer(data, dtype=np.float32)

                    if dev_channels > 1:
                        mono = audio.reshape(-1, dev_channels)[:, 0]
                    else:
                        mono = audio

                    buffer = np.concatenate([buffer, mono])

                    while len(buffer) >= chunk_samples_native:
                        chunk_native = buffer[:chunk_samples_native].copy()
                        buffer = buffer[chunk_samples_native:]

                        energy = np.sqrt(np.mean(chunk_native ** 2))
                        if energy > self.silence_threshold:
                            chunk_16k = self._resample_to_16k(chunk_native, native_sr)
                            self._audio_queue.put(("mic", chunk_16k))

                except IOError as e:
                    print(f"[audio] Mic read error: {e}")
                    continue

            stream.stop_stream()
            stream.close()

        except Exception as e:
            print(f"[audio] Mic ERROR: {e}")
        finally:
            p.terminate()

    def _dispatch_chunks(self):
        """Dispatch audio chunks from the queue to the callback."""
        while self._running:
            try:
                source, chunk = self._audio_queue.get(timeout=0.5)
                if self.on_audio_chunk:
                    self.on_audio_chunk(chunk, source)
            except queue.Empty:
                continue

    def start(self):
        """Start capturing audio."""
        if self._running:
            return

        self._running = True

        # System audio thread (WASAPI loopback)
        self._system_thread = threading.Thread(
            target=self._capture_system_audio, daemon=True, name="SystemAudio"
        )
        self._system_thread.start()

        # Mic thread (optional)
        if self.capture_mic:
            self._mic_thread = threading.Thread(
                target=self._capture_mic_audio, daemon=True, name="MicAudio"
            )
            self._mic_thread.start()

        # Dispatcher thread
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_chunks, daemon=True, name="AudioDispatch"
        )
        self._dispatch_thread.start()

        print(f"[audio] Capture started (chunk={self.chunk_duration}s, target={self.target_sample_rate}Hz)")

    def stop(self):
        """Stop capturing audio."""
        self._running = False
        if self._system_thread:
            self._system_thread.join(timeout=3)
        if self._mic_thread:
            self._mic_thread.join(timeout=3)
        print(f"[audio] Capture stopped")

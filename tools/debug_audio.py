"""
Audio Debug Tool
================
Tests WASAPI loopback capture using PyAudioWPatch.

Usage:
    1. Play audio on your speakers (YouTube, music, etc.)
    2. Run: python tools/debug_audio.py
"""

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def main():
    print("\n" + "=" * 50)
    print("  CLUELY AUDIO DEBUG (PyAudioWPatch)")
    print("=" * 50)

    # =========================================================
    # Step 1: Find WASAPI loopback device
    # =========================================================
    print(f"\n--- Step 1: Find WASAPI Loopback Device ---")

    import pyaudiowpatch as pyaudio

    p = pyaudio.PyAudio()

    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        print("  FATAL: WASAPI not available on this system!")
        p.terminate()
        return

    print(f"  WASAPI Host API: index={wasapi_info['index']}, devices={wasapi_info['deviceCount']}")

    # Get default speakers
    default_output_idx = wasapi_info["defaultOutputDevice"]
    default_speakers = p.get_device_info_by_index(default_output_idx)

    print(f"  Default speakers: [{default_output_idx}] {default_speakers['name']}")
    print(f"  Sample rate: {int(default_speakers['defaultSampleRate'])}Hz")
    print(f"  Max output channels: {default_speakers['maxOutputChannels']}")

    # Find the loopback device for this speaker
    loopback_device = None
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev.get("isLoopbackDevice", False):
            # Match to our default speakers
            if dev['name'].startswith(default_speakers['name'].split('(')[0].strip()):
                loopback_device = dev
                print(f"  Loopback device: [{i}] {dev['name']}")
                break

    if loopback_device is None:
        # Try finding any loopback device
        print(f"  No exact match, searching all loopback devices...")
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev.get("isLoopbackDevice", False):
                loopback_device = dev
                print(f"  Found loopback: [{i}] {dev['name']}")
                break

    if loopback_device is None:
        print(f"  FATAL: No loopback device found!")
        p.terminate()
        return

    native_sr = int(loopback_device['defaultSampleRate'])
    channels = loopback_device['maxInputChannels']
    print(f"\n  Using: {loopback_device['name']}")
    print(f"  Sample rate: {native_sr}Hz, Channels: {channels}")

    # =========================================================
    # Step 2: Capture audio
    # =========================================================
    print(f"\n--- Step 2: Capture 5 seconds of system audio ---")
    print(f"  >>> PLAY AUDIO ON YOUR SPEAKERS NOW! <<<")
    print(f"  (YouTube video, music, anything...)")

    frames = []
    CHUNK = 1024

    try:
        stream = p.open(
            format=pyaudio.paFloat32,
            channels=channels,
            rate=native_sr,
            input=True,
            input_device_index=loopback_device['index'],
            frames_per_buffer=CHUNK,
        )

        total_chunks = int(native_sr / CHUNK * 5)  # 5 seconds

        for i in range(total_chunks):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(np.frombuffer(data, dtype=np.float32))

            # Progress every second
            elapsed = (i + 1) * CHUNK / native_sr
            if abs(elapsed % 1.0) < (CHUNK / native_sr):
                sample_count = sum(len(f) for f in frames)
                print(f"    {int(elapsed)}s: {sample_count} samples captured")

        stream.stop_stream()
        stream.close()

    except Exception as e:
        print(f"  ERROR: {e}")
        p.terminate()
        return

    # Analyze
    audio = np.concatenate(frames)
    print(f"\n  Total captured: {len(audio)} samples ({len(audio)/native_sr/channels:.1f}s)")

    # Convert to mono
    if channels > 1:
        mono = audio.reshape(-1, channels)[:, 0]
    else:
        mono = audio

    energy = np.sqrt(np.mean(mono ** 2))
    max_val = np.max(np.abs(mono))
    print(f"  Energy (RMS): {energy:.6f}")
    print(f"  Max amplitude: {max_val:.6f}")

    if energy < 0.0001:
        print(f"  WARNING: Audio seems silent! Was audio playing?")
        p.terminate()
        return
    else:
        print(f"  AUDIO CAPTURED SUCCESSFULLY!")

    # =========================================================
    # Step 3: Resample to 16kHz
    # =========================================================
    print(f"\n--- Step 3: Resample {native_sr}Hz -> 16000Hz ---")

    from scipy.signal import resample

    target_samples = int(len(mono) * 16000 / native_sr)
    resampled = resample(mono, target_samples).astype(np.float32)

    print(f"  Original: {len(mono)} samples at {native_sr}Hz")
    print(f"  Resampled: {len(resampled)} samples at 16000Hz")
    print(f"  Duration: {len(resampled)/16000:.1f}s")

    # =========================================================
    # Step 4: Whisper transcription
    # =========================================================
    print(f"\n--- Step 4: Whisper Transcription ---")

    try:
        from faster_whisper import WhisperModel

        print(f"  Loading Whisper base model...")
        model = WhisperModel("base", device="cpu", compute_type="int8")

        print(f"  Transcribing...")
        start = time.time()
        segments, info = model.transcribe(resampled, beam_size=1, language="en", vad_filter=True)
        text = " ".join(s.text.strip() for s in segments)
        elapsed = time.time() - start

        print(f"  Time: {elapsed:.2f}s")
        print(f"  Transcript: \"{text}\"")

        if text.strip():
            print(f"\n  FULL PIPELINE WORKS!")
            print(f"  PyAudioWPatch({native_sr}Hz) -> Resample(16kHz) -> Whisper -> Text")
        else:
            print(f"  Whisper returned empty (audio may have been speech-less)")

    except Exception as e:
        print(f"  Whisper error: {e}")

    p.terminate()

    print(f"\n{'='*50}")
    print(f"  DEBUG COMPLETE")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()

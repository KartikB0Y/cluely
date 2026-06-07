"""
Cluely Latency Test
====================
Benchmarks STT (Speech-to-Text) providers on your hardware.

Tests:
1. Whisper model loading time
2. Whisper transcription latency (per chunk)
3. Deepgram latency (if API key configured)
4. End-to-end pipeline latency estimate

Usage:
    python tools/latency_test.py                # Test default provider
    python tools/latency_test.py --all          # Test all providers
    python tools/latency_test.py --record       # Record live audio and test
    python tools/latency_test.py --duration 10  # Record 10 seconds
"""

import sys
import os
import time
import argparse
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def generate_test_audio(duration_seconds=5, sample_rate=16000):
    """Generate synthetic audio with speech-like characteristics for testing."""
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), dtype=np.float32)
    # Mix of frequencies that resemble speech
    audio = (
        0.3 * np.sin(2 * np.pi * 150 * t) +   # fundamental
        0.2 * np.sin(2 * np.pi * 300 * t) +   # harmonic
        0.1 * np.sin(2 * np.pi * 600 * t) +   # harmonic
        0.05 * np.random.randn(len(t))          # noise
    ).astype(np.float32)
    return audio


def record_audio(duration_seconds=5, sample_rate=16000):
    """Record live audio from the default input device."""
    try:
        import sounddevice as sd
        print(f"  Recording {duration_seconds}s of audio... Speak now!")
        audio = sd.rec(
            int(duration_seconds * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='float32'
        )
        sd.wait()
        print(f"  Recording complete.")
        return audio.flatten()
    except Exception as e:
        print(f"  [ERROR] Could not record audio: {e}")
        print(f"  Using synthetic audio instead.")
        return generate_test_audio(duration_seconds, sample_rate)


def test_whisper_latency(audio_data, sample_rate=16000):
    """Benchmark faster-whisper on the given audio."""
    results = {}

    try:
        from faster_whisper import WhisperModel
        from config import WHISPER_MODEL_SIZE, WHISPER_COMPUTE_TYPE
    except ImportError as e:
        print(f"  [SKIP] Whisper not available: {e}")
        return None

    model_size = WHISPER_MODEL_SIZE
    print(f"\n  --- Whisper ({model_size}) Benchmark ---")

    # Test 1: Model loading time
    print(f"  Loading model '{model_size}'...")
    start = time.time()
    model = WhisperModel(model_size, device="cpu", compute_type=WHISPER_COMPUTE_TYPE)
    load_time = time.time() - start
    results["model_load_time"] = load_time
    print(f"  Model load time: {load_time:.2f}s")

    # Test 2: Transcription latency (run 3 times, take average)
    audio_duration = len(audio_data) / sample_rate
    print(f"  Audio duration: {audio_duration:.1f}s")
    print(f"  Running 3 transcription passes...")

    latencies = []
    transcripts = []
    for i in range(3):
        start = time.time()
        segments, info = model.transcribe(
            audio_data,
            beam_size=1,           # Greedy = fastest
            language="en",
            vad_filter=True,
        )
        # Force evaluation of generator
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text)
        elapsed = time.time() - start
        latencies.append(elapsed)
        transcript = " ".join(text_parts).strip()
        transcripts.append(transcript)
        print(f"    Pass {i+1}: {elapsed:.3f}s | \"{transcript[:80]}{'...' if len(transcript) > 80 else ''}\"")

    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)

    results["avg_latency"] = avg_latency
    results["min_latency"] = min_latency
    results["max_latency"] = max_latency
    results["transcript"] = transcripts[-1]
    results["realtime_factor"] = avg_latency / audio_duration

    print(f"\n  Whisper Results:")
    print(f"    Average latency:  {avg_latency:.3f}s")
    print(f"    Min latency:      {min_latency:.3f}s")
    print(f"    Max latency:      {max_latency:.3f}s")
    print(f"    Real-time factor: {results['realtime_factor']:.2f}x (< 1.0 = faster than real-time)")
    print(f"    Model size:       {model_size}")
    print(f"    Compute type:     {WHISPER_COMPUTE_TYPE}")

    del model
    return results


def test_deepgram_latency(audio_data, sample_rate=16000):
    """Benchmark Deepgram cloud STT."""
    try:
        from config import DEEPGRAM_API_KEY
        if not DEEPGRAM_API_KEY:
            print(f"\n  [SKIP] Deepgram: No API key configured in config.py")
            return None
    except ImportError:
        print(f"\n  [SKIP] Deepgram: config.py not found")
        return None

    try:
        from deepgram import DeepgramClient, PrerecordedOptions
    except ImportError:
        print(f"\n  [SKIP] Deepgram: deepgram-sdk not installed (pip install deepgram-sdk)")
        return None

    results = {}
    print(f"\n  --- Deepgram (nova-2) Benchmark ---")

    # Convert float32 audio to int16 bytes
    audio_int16 = (audio_data * 32767).astype(np.int16)
    audio_bytes = audio_int16.tobytes()
    audio_duration = len(audio_data) / sample_rate

    print(f"  Audio duration: {audio_duration:.1f}s")
    print(f"  Running 3 transcription passes...")

    latencies = []
    transcripts = []

    try:
        client = DeepgramClient(DEEPGRAM_API_KEY)

        for i in range(3):
            start = time.time()
            response = client.listen.rest.v("1").transcribe_file(
                {"buffer": audio_bytes, "mimetype": "audio/raw"},
                PrerecordedOptions(
                    model="nova-2",
                    language="en",
                    encoding="linear16",
                    sample_rate=sample_rate,
                    channels=1,
                ),
            )
            elapsed = time.time() - start
            latencies.append(elapsed)

            transcript = response.results.channels[0].alternatives[0].transcript
            transcripts.append(transcript)
            print(f"    Pass {i+1}: {elapsed:.3f}s | \"{transcript[:80]}{'...' if len(transcript) > 80 else ''}\"")

        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        results["avg_latency"] = avg_latency
        results["min_latency"] = min_latency
        results["max_latency"] = max_latency
        results["transcript"] = transcripts[-1]
        results["realtime_factor"] = avg_latency / audio_duration

        print(f"\n  Deepgram Results:")
        print(f"    Average latency:  {avg_latency:.3f}s")
        print(f"    Min latency:      {min_latency:.3f}s")
        print(f"    Max latency:      {max_latency:.3f}s")
        print(f"    Real-time factor: {results['realtime_factor']:.2f}x")
        print(f"    Model:            nova-2")

    except Exception as e:
        print(f"  [ERROR] Deepgram test failed: {e}")
        return None

    return results


def test_audio_devices():
    """List and test available audio devices."""
    print(f"\n  --- Audio Devices ---")
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        print(f"  Found {len(devices)} audio devices:\n")

        for i, dev in enumerate(devices):
            direction = ""
            if dev['max_input_channels'] > 0:
                direction += "IN"
            if dev['max_output_channels'] > 0:
                direction += ("+" if direction else "") + "OUT"

            marker = ""
            if i == sd.default.device[0]:
                marker += " << DEFAULT INPUT"
            if i == sd.default.device[1]:
                marker += " << DEFAULT OUTPUT"

            # Check for WASAPI loopback
            name = dev['name']
            hostapi = sd.query_hostapis(dev['hostapi'])['name']

            print(f"    [{i:2d}] {name}")
            print(f"         Host: {hostapi} | {direction} | SR: {dev['default_samplerate']:.0f}Hz{marker}")

        # Check for WASAPI
        print(f"\n  Looking for WASAPI loopback devices...")
        wasapi_found = False
        for i, dev in enumerate(devices):
            hostapi = sd.query_hostapis(dev['hostapi'])['name']
            if 'WASAPI' in hostapi and dev['max_input_channels'] > 0:
                if 'loopback' in dev['name'].lower() or dev['max_output_channels'] > 0:
                    print(f"    [OK] WASAPI device [{i}]: {dev['name']}")
                    wasapi_found = True

        if not wasapi_found:
            print(f"    [INFO] No WASAPI loopback label found.")
            print(f"    sounddevice may need the WASAPI loopback flag set at stream creation time.")
            print(f"    This is normal - the audio_capture module handles this.")

    except ImportError:
        print(f"  [ERROR] sounddevice not installed (pip install sounddevice)")
    except Exception as e:
        print(f"  [ERROR] {e}")


def print_comparison(whisper_results, deepgram_results):
    """Print a side-by-side comparison table."""
    print(f"\n{'='*60}")
    print(f"  COMPARISON TABLE")
    print(f"{'='*60}")
    print(f"  {'Metric':<25} {'Whisper (local)':<18} {'Deepgram (cloud)':<18}")
    print(f"  {'-'*25} {'-'*18} {'-'*18}")

    w = whisper_results or {}
    d = deepgram_results or {}

    def fmt(val, suffix="s"):
        return f"{val:.3f}{suffix}" if val is not None else "N/A"

    rows = [
        ("Avg Latency", w.get("avg_latency"), d.get("avg_latency"), "s"),
        ("Min Latency", w.get("min_latency"), d.get("min_latency"), "s"),
        ("Max Latency", w.get("max_latency"), d.get("max_latency"), "s"),
        ("Real-time Factor", w.get("realtime_factor"), d.get("realtime_factor"), "x"),
    ]

    for name, wval, dval, suffix in rows:
        wcol = fmt(wval, suffix) if wval is not None else "N/A"
        dcol = fmt(dval, suffix) if dval is not None else "N/A"
        print(f"  {name:<25} {wcol:<18} {dcol:<18}")

    # Recommendation
    print(f"\n  RECOMMENDATION:")
    if whisper_results and whisper_results.get("avg_latency", 99) < 4:
        print(f"  >> Whisper is fast enough on your CPU ({whisper_results['avg_latency']:.1f}s avg).")
        print(f"     Stick with local Whisper to save costs.")
    elif whisper_results:
        print(f"  >> Whisper is slow on your CPU ({whisper_results['avg_latency']:.1f}s avg).")
        if deepgram_results:
            print(f"     Consider switching to Deepgram ({deepgram_results['avg_latency']:.1f}s avg).")
        else:
            print(f"     Consider trying Deepgram for lower latency.")
            print(f"     Set DEEPGRAM_API_KEY in config.py and re-run this test.")

    if whisper_results:
        rtf = whisper_results.get("realtime_factor", 99)
        if rtf < 0.5:
            print(f"  >> Real-time factor {rtf:.2f}x - Excellent! Much faster than real-time.")
        elif rtf < 1.0:
            print(f"  >> Real-time factor {rtf:.2f}x - Good. Faster than real-time.")
        else:
            print(f"  >> Real-time factor {rtf:.2f}x - Slower than real-time. Consider 'tiny' model.")
            print(f"     Change WHISPER_MODEL_SIZE = 'tiny' in config.py")

    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Cluely STT Latency Benchmark")
    parser.add_argument("--all", action="store_true", help="Test all available providers")
    parser.add_argument("--record", action="store_true", help="Record live audio for testing")
    parser.add_argument("--duration", type=int, default=5, help="Recording duration in seconds (default: 5)")
    parser.add_argument("--devices", action="store_true", help="List audio devices and exit")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  CLUELY - STT Latency Benchmark")
    print("=" * 60)

    # System info
    import platform
    print(f"  Platform:  {platform.platform()}")
    print(f"  Processor: {platform.processor()}")
    print(f"  Python:    {platform.python_version()}")

    # List audio devices
    test_audio_devices()

    if args.devices:
        return

    # Get test audio
    print(f"\n  --- Preparing Test Audio ---")
    if args.record:
        audio_data = record_audio(args.duration)
    else:
        print(f"  Using synthetic test audio ({args.duration}s)")
        print(f"  Tip: Use --record to test with real speech for accuracy comparison")
        audio_data = generate_test_audio(args.duration)

    sample_rate = 16000

    # Run benchmarks
    whisper_results = None
    deepgram_results = None

    try:
        from config import STT_PROVIDER
    except ImportError:
        STT_PROVIDER = "whisper"

    if args.all or STT_PROVIDER == "whisper":
        whisper_results = test_whisper_latency(audio_data, sample_rate)

    if args.all or STT_PROVIDER == "deepgram":
        deepgram_results = test_deepgram_latency(audio_data, sample_rate)

    # Comparison
    if whisper_results or deepgram_results:
        print_comparison(whisper_results, deepgram_results)

    # Pipeline estimate
    print(f"  --- Estimated End-to-End Pipeline Latency ---")
    print(f"  (Audio chunk duration: 5s)")
    print(f"  (Claude Haiku 4.5 streaming: ~0.5s to first token)")
    print()

    if whisper_results:
        total = whisper_results["avg_latency"] + 0.5  # + Claude latency
        print(f"  With Whisper: ~{total:.1f}s from end of speech to AI response")

    if deepgram_results:
        total = deepgram_results["avg_latency"] + 0.5
        print(f"  With Deepgram: ~{total:.1f}s from end of speech to AI response")

    print()


if __name__ == "__main__":
    main()

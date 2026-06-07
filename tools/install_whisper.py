"""
Whisper Model Installer
=======================
Downloads and caches the faster-whisper model. Skips if already installed.

Usage:
    python tools/install_whisper.py              # Install default (base) model
    python tools/install_whisper.py tiny          # Install tiny model
    python tools/install_whisper.py base small    # Install multiple models
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def get_model_info():
    """Model sizes and approximate download sizes."""
    return {
        "tiny":   {"params": "39M",  "size": "~75 MB",  "cpu_speed": "~1-2s / 5s audio"},
        "base":   {"params": "74M",  "size": "~150 MB", "cpu_speed": "~2-4s / 5s audio"},
        "small":  {"params": "244M", "size": "~500 MB", "cpu_speed": "~5-10s / 5s audio"},
        "medium": {"params": "769M", "size": "~1.5 GB", "cpu_speed": "~15-30s / 5s audio"},
        "large":  {"params": "1550M","size": "~3 GB",   "cpu_speed": "~30-60s / 5s audio"},
    }


def check_model_exists(model_size):
    """Check if the model is already cached by faster-whisper."""
    try:
        from faster_whisper.utils import download_model
        # faster-whisper caches models in a standard location
        # We can check by trying to get the model path
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
        model_name = f"models--Systran--faster-whisper-{model_size}"
        model_path = os.path.join(cache_dir, model_name)

        if os.path.exists(model_path):
            # Check if the snapshots directory has content
            snapshots_dir = os.path.join(model_path, "snapshots")
            if os.path.exists(snapshots_dir) and os.listdir(snapshots_dir):
                return True
        return False
    except ImportError:
        return False


def install_model(model_size):
    """Download and cache the Whisper model."""
    models = get_model_info()

    if model_size not in models:
        print(f"  [ERROR] Unknown model: '{model_size}'")
        print(f"  Available models: {', '.join(models.keys())}")
        return False

    info = models[model_size]
    print(f"\n{'='*60}")
    print(f"  Model: {model_size}")
    print(f"  Parameters: {info['params']}")
    print(f"  Download size: {info['size']}")
    print(f"  Expected CPU speed: {info['cpu_speed']}")
    print(f"{'='*60}")

    # Check if already installed
    if check_model_exists(model_size):
        print(f"  [OK] Model '{model_size}' is already installed. Skipping download.")
        # Verify it loads correctly
        print(f"  Verifying model loads correctly...")
        try:
            from faster_whisper import WhisperModel
            start = time.time()
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            load_time = time.time() - start
            print(f"  [OK] Model loaded successfully in {load_time:.1f}s")
            del model
            return True
        except Exception as e:
            print(f"  [WARN] Model exists but failed to load: {e}")
            print(f"  Re-downloading...")

    # Download the model
    print(f"\n  Downloading '{model_size}' model... (this may take a few minutes)")
    print(f"  The model will be cached at: ~/.cache/huggingface/hub/")

    try:
        from faster_whisper import WhisperModel

        start = time.time()
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        download_time = time.time() - start

        print(f"  [OK] Model '{model_size}' downloaded and loaded in {download_time:.1f}s")
        del model
        return True

    except ImportError:
        print(f"  [ERROR] faster-whisper is not installed!")
        print(f"  Run: pip install faster-whisper>=1.0.0")
        return False
    except Exception as e:
        print(f"  [ERROR] Failed to download model: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("  CLUELY - Whisper Model Installer")
    print("=" * 60)

    # Check if faster-whisper is installed
    try:
        import faster_whisper
        print(f"  faster-whisper version: {faster_whisper.__version__}")
    except ImportError:
        print("  [ERROR] faster-whisper is not installed!")
        print("  Run: pip install faster-whisper>=1.0.0")
        print("  Or:  pip install -r requirements.txt")
        sys.exit(1)

    # Determine which models to install
    if len(sys.argv) > 1:
        models_to_install = sys.argv[1:]
    else:
        # Default: install the model from config
        try:
            from config import WHISPER_MODEL_SIZE
            models_to_install = [WHISPER_MODEL_SIZE]
            print(f"  Installing default model from config: {WHISPER_MODEL_SIZE}")
        except ImportError:
            models_to_install = ["base"]
            print(f"  Installing default model: base")

    # Install each model
    results = {}
    for model_size in models_to_install:
        success = install_model(model_size)
        results[model_size] = success

    # Summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for model, success in results.items():
        status = "[OK] Installed" if success else "[FAILED]"
        print(f"  {model}: {status}")

    print(f"\n  Models are cached at: ~/.cache/huggingface/hub/")
    print(f"  To change the default model, edit WHISPER_MODEL_SIZE in config.py")
    print(f"{'='*60}\n")

    # Return exit code
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Constants for Audio Transcriber application."""

# Audio file extensions supported
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.webm'}

# Model specifications for different Whisper model sizes
MODEL_SPECS = {
    "tiny": {
        "params": "39M",
        "vram": "~0.2GB",
        "speed": "Very Fast (30-50x real-time on GPU)",
        "accuracy": "Basic",
        "use_case": "Quick drafts, testing",
        "download": "~75MB"
    },
    "base": {
        "params": "74M",
        "vram": "~0.5GB",
        "speed": "Fast (20-40x real-time on GPU)",
        "accuracy": "Good",
        "use_case": "General purpose - RECOMMENDED",
        "download": "~150MB"
    },
    "small": {
        "params": "244M",
        "vram": "~1GB",
        "speed": "Medium (10-20x real-time on GPU)",
        "accuracy": "Better",
        "use_case": "High quality transcripts",
        "download": "~500MB"
    },
    "medium": {
        "params": "769M",
        "vram": "~2GB",
        "speed": "Slower (5-10x real-time on GPU)",
        "accuracy": "High",
        "use_case": "Professional transcription",
        "download": "~1.5GB"
    },
    "large-v3": {
        "params": "1550M",
        "vram": "~6GB",
        "speed": "Slowest (2-5x real-time on GPU)",
        "accuracy": "Highest",
        "use_case": "Critical accuracy needs",
        "download": "~3GB"
    },
    "turbo": {
        "params": "809M",
        "vram": "~3GB",
        "speed": "Optimized (8-15x real-time on GPU)",
        "accuracy": "High",
        "use_case": "Balanced speed & quality",
        "download": "~1.6GB"
    }
}

# Available model sizes
MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v3", "turbo"]

# Available compute types
COMPUTE_TYPES = ["float16", "int8", "int8_float16"]

# Available engines
ENGINES = ["auto_gpu", "faster_whisper_gpu", "faster_whisper_cpu", "whisper_gpu", "whisper_cpu"]

# Timestamp settings
TIMESTAMP_FORMATS = ["HH:MM:SS", "MM:SS", "timecode"]
# Available timestamp intervals (in seconds), used with IntVar in the UI:
# 15s, 30s, 1min (60s), 2min (120s), 5min (300s), 10min (600s)
TIMESTAMP_INTERVALS = [15, 30, 60, 120, 300, 600]
DEFAULT_TIMESTAMP_FORMAT = "HH:MM:SS"
DEFAULT_TIMESTAMP_INTERVAL = 30  # seconds (30s)

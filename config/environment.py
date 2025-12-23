"""Environment detection for Audio Transcriber."""
import torch

# Try to import audio libraries
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

try:
    import wave
    WAVE_AVAILABLE = True
except ImportError:
    WAVE_AVAILABLE = False

try:
    from mutagen.id3 import ID3
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

# Try to import GPU-accelerated libraries
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False


class Environment:
    """Manages environment detection and library availability."""
    
    def __init__(self):
        """Initialize environment detection."""
        self.pydub_available = PYDUB_AVAILABLE
        self.wave_available = WAVE_AVAILABLE
        self.mutagen_available = MUTAGEN_AVAILABLE
        self.whisper_available = WHISPER_AVAILABLE
        self.faster_whisper_available = FASTER_WHISPER_AVAILABLE
        
        # GPU detection
        self.gpu_available = torch.cuda.is_available()
        self.device = "cuda" if self.gpu_available else "cpu"
        
    def get_gpu_info(self):
        """Get GPU information."""
        if self.gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
            memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            return {
                'available': True,
                'name': gpu_name,
                'memory_gb': memory
            }
        return {'available': False}
    
    def get_gpu_status_text(self):
        """Get human-readable GPU status."""
        if self.gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
            memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            return f"✅ GPU Available: {gpu_name} ({memory:.1f}GB VRAM)"
        return "❌ No GPU detected - CPU mode only (slower processing)"
    
    def get_library_status(self):
        """Get status of all libraries."""
        return {
            'pydub': self.pydub_available,
            'wave': self.wave_available,
            'mutagen': self.mutagen_available,
            'whisper': self.whisper_available,
            'faster_whisper': self.faster_whisper_available
        }

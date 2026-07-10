"""Environment detection for Audio Transcriber."""
import os

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

# Try to import audio libraries
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except Exception:
    PYDUB_AVAILABLE = False

try:
    import wave
    WAVE_AVAILABLE = True
except Exception:
    WAVE_AVAILABLE = False

try:
    from mutagen.id3 import ID3
    MUTAGEN_AVAILABLE = True
except Exception:
    MUTAGEN_AVAILABLE = False

# Try to import GPU-accelerated libraries
try:
    import whisper
    WHISPER_AVAILABLE = True
except Exception:
    WHISPER_AVAILABLE = False

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except Exception:
    FASTER_WHISPER_AVAILABLE = False

try:
    import warnings
    # Suppress torchcodec warnings from pyannote.audio (uses av library as fallback)
    warnings.filterwarnings('ignore', category=UserWarning, module='pyannote.audio.core.io')
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except Exception:
    PYANNOTE_AVAILABLE = False


class Environment:
    """Manages environment detection and library availability."""
    
    def __init__(self):
        """Initialize environment detection."""
        self.pydub_available = PYDUB_AVAILABLE
        self.wave_available = WAVE_AVAILABLE
        self.mutagen_available = MUTAGEN_AVAILABLE
        self.whisper_available = WHISPER_AVAILABLE
        self.faster_whisper_available = FASTER_WHISPER_AVAILABLE
        self.pyannote_available = PYANNOTE_AVAILABLE
        
        # GPU detection
        self.gpu_available = bool(TORCH_AVAILABLE and torch.cuda.is_available())
        self.device = "cuda" if self.gpu_available else "cpu"
        self._gpu_name = None
        self._gpu_memory_gb = None
        if self.gpu_available:
            try:
                self._gpu_name = torch.cuda.get_device_name(0)
                self._gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            except Exception:
                self.gpu_available = False
                self.device = "cpu"
                self._gpu_name = None
                self._gpu_memory_gb = None
        
    def get_gpu_info(self):
        """Get GPU information."""
        if self.gpu_available:
            return {
                'available': True,
                'name': self._gpu_name,
                'memory_gb': self._gpu_memory_gb
            }
        return {'available': False}
    
    def get_gpu_status_text(self):
        """Get human-readable GPU status."""
        if self.gpu_available:
            return f"✅ GPU Available: {self._gpu_name} ({self._gpu_memory_gb:.1f}GB VRAM)"
        return "❌ No GPU detected - CPU mode only (slower processing)"
    
    def get_library_status(self):
        """Get status of all libraries."""
        return {
            'torch': TORCH_AVAILABLE,
            'pydub': self.pydub_available,
            'wave': self.wave_available,
            'mutagen': self.mutagen_available,
            'whisper': self.whisper_available,
            'faster_whisper': self.faster_whisper_available,
            'pyannote': self.pyannote_available
        }
    
    def resolve_engine(self, engine: str) -> str:
        """Resolve 'auto_gpu' to specific engine based on availability.
        
        Args:
            engine: Engine type (auto_gpu, whisper_gpu, whisper_cpu, faster_whisper_gpu, faster_whisper_cpu).
            
        Returns:
            Resolved engine type.
        """
        if engine == "auto_gpu":
            if FASTER_WHISPER_AVAILABLE and self.gpu_available:
                return "faster_whisper_gpu"
            elif WHISPER_AVAILABLE and self.gpu_available:
                return "whisper_gpu"
            elif FASTER_WHISPER_AVAILABLE:
                return "faster_whisper_cpu"
            elif WHISPER_AVAILABLE:
                return "whisper_cpu"
        
        return engine
    
    def is_engine_available(self, engine: str) -> bool:
        """Check if a specific transcription engine is available.
        
        Args:
            engine: Engine name ('whisper', 'faster_whisper', 'auto_gpu').
            
        Returns:
            True if engine is available, False otherwise.
        """
        if engine == 'auto_gpu':
            return True  # auto_gpu always available as fallback
        elif engine == 'whisper':
            return self.whisper_available
        elif engine == 'faster_whisper':
            return self.faster_whisper_available
        return False
    
    def get_diarization_device(self, whisper_loaded: bool = False) -> str:
        """Determine device for speaker diarization.
        
        Args:
            whisper_loaded: Whether Whisper model is currently loaded in GPU memory.
            
        Returns:
            Device string ('cuda' or 'cpu').
        """
        forced = os.environ.get("AUDIO_TRANSCRIBER_DIARIZATION_DEVICE", "auto").strip().lower()
        if forced in {"cpu", "cuda"}:
            if forced == "cuda" and not self.gpu_available:
                return "cpu"
            return forced

        if not self.gpu_available or not TORCH_AVAILABLE:
            return "cpu"

        # If transcription model is already on GPU, ensure enough free VRAM
        # before placing pyannote there as well.
        if whisper_loaded:
            try:
                memory_gb = self._gpu_memory_gb or 0.0
                used_memory = torch.cuda.memory_allocated(0) / (1024**3)
                available = memory_gb - used_memory

                # Keep a larger buffer for stability on long diarization runs.
                return "cuda" if available > 3.5 else "cpu"
            except Exception:
                return "cpu"

        return "cuda"

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

try:
    import warnings
    # Suppress torchcodec warnings from pyannote.audio (uses av library as fallback)
    warnings.filterwarnings('ignore', category=UserWarning, module='pyannote.audio.core.io')
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
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
        if not self.gpu_available:
            return "cpu"
        
        # Check available VRAM if Whisper is already loaded
        if whisper_loaded:
            try:
                memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                used_memory = torch.cuda.memory_allocated(0) / (1024**3)
                available = memory_gb - used_memory
                
                # pyannote needs ~2GB VRAM
                if available > 2.5:
                    return "cuda"
                else:
                    return "cpu"  # Not enough VRAM, fallback to CPU
            except Exception:
                return "cpu"  # Error checking VRAM, play it safe
        
        return "cuda"  # GPU available and nothing loaded yet

"""Model manager for Audio Transcriber."""
import torch
from pathlib import Path
from config.environment import WHISPER_AVAILABLE, FASTER_WHISPER_AVAILABLE

if WHISPER_AVAILABLE:
    import whisper

if FASTER_WHISPER_AVAILABLE:
    from faster_whisper import WhisperModel


class ModelManager:
    """Manages Whisper model loading, caching, and cleanup."""
    
    def __init__(self, environment):
        """Initialize model manager.
        
        Args:
            environment: Environment instance with GPU detection.
        """
        self.environment = environment
        self.whisper_model = None
        self.faster_whisper_model = None
        
    def load_model(self, engine, model_size, compute_type):
        """Load transcription model.
        
        Args:
            engine: Engine type (auto_gpu, whisper_gpu, whisper_cpu, faster_whisper_gpu, faster_whisper_cpu).
            model_size: Model size (tiny, base, small, medium, large-v3, turbo).
            compute_type: Compute precision (float16, int8, int8_float16).
        """
        # Resolve auto_gpu to specific engine
        actual_engine = engine
        if engine == "auto_gpu":
            if FASTER_WHISPER_AVAILABLE and self.environment.gpu_available:
                actual_engine = "faster_whisper_gpu"
            elif WHISPER_AVAILABLE and self.environment.gpu_available:
                actual_engine = "whisper_gpu"
            elif FASTER_WHISPER_AVAILABLE:
                actual_engine = "faster_whisper_cpu"
            elif WHISPER_AVAILABLE:
                actual_engine = "whisper_cpu"
        
        # Load appropriate model
        if actual_engine.startswith("faster_whisper"):
            device = "cuda" if actual_engine.endswith("_gpu") and self.environment.gpu_available else "cpu"
            self.faster_whisper_model = WhisperModel(
                model_size, device=device, compute_type=compute_type)
        elif actual_engine.startswith("whisper"):
            device = self.environment.device if actual_engine.endswith("_gpu") else "cpu"
            self.whisper_model = whisper.load_model(model_size, device=device)
    
    def cleanup_model(self):
        """Clean up models and free GPU memory."""
        if self.faster_whisper_model:
            del self.faster_whisper_model
            self.faster_whisper_model = None
        if self.whisper_model:
            del self.whisper_model
            self.whisper_model = None
        if self.environment.gpu_available:
            torch.cuda.empty_cache()
    
    def check_model_downloaded(self, model_size):
        """Check if a model is already downloaded.
        
        Args:
            model_size: Model size to check.
            
        Returns:
            Tuple of (whisper_downloaded, faster_whisper_downloaded).
        """
        whisper_downloaded = False
        faster_whisper_downloaded = False
        
        # Check Whisper cache
        if WHISPER_AVAILABLE:
            cache_dir = Path.home() / ".cache" / "whisper"
            if cache_dir.exists():
                model_file = cache_dir / f"{model_size}.pt"
                whisper_downloaded = model_file.exists()
        
        # Check Faster-Whisper cache (stored in huggingface hub cache)
        if FASTER_WHISPER_AVAILABLE:
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
            if cache_dir.exists():
                # Faster-whisper models are stored with different naming
                faster_whisper_downloaded = any(
                    f"models--Systran--faster-whisper-{model_size}" in str(p)
                    for p in cache_dir.glob("*")
                )
        
        return whisper_downloaded, faster_whisper_downloaded
    
    def download_model(self, model_size, engine, compute_type):
        """Download a specific model.
        
        Args:
            model_size: Model size to download.
            engine: Engine type.
            compute_type: Compute precision.
        """
        # Resolve auto_gpu
        actual_engine = engine
        if engine == "auto_gpu":
            if FASTER_WHISPER_AVAILABLE and self.environment.gpu_available:
                actual_engine = "faster_whisper_gpu"
            elif WHISPER_AVAILABLE and self.environment.gpu_available:
                actual_engine = "whisper_gpu"
            elif FASTER_WHISPER_AVAILABLE:
                actual_engine = "faster_whisper_cpu"
            elif WHISPER_AVAILABLE:
                actual_engine = "whisper_cpu"
        
        # Download by loading the model
        if actual_engine.startswith("faster_whisper") and FASTER_WHISPER_AVAILABLE:
            device = "cuda" if actual_engine.endswith("_gpu") and self.environment.gpu_available else "cpu"
            temp_model = WhisperModel(model_size, device=device, compute_type=compute_type)
            del temp_model
            
        if actual_engine.startswith("whisper") and WHISPER_AVAILABLE:
            device = self.environment.device if actual_engine.endswith("_gpu") else "cpu"
            temp_model = whisper.load_model(model_size, device=device)
            del temp_model
            
        if self.environment.gpu_available:
            torch.cuda.empty_cache()
    
    def get_active_model(self):
        """Get the currently active model.
        
        Returns:
            Tuple of (model, model_type) where model_type is 'whisper' or 'faster_whisper'.
        """
        if self.faster_whisper_model:
            return self.faster_whisper_model, 'faster_whisper'
        elif self.whisper_model:
            return self.whisper_model, 'whisper'
        return None, None

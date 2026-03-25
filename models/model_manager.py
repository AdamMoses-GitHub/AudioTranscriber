"""Model manager for Audio Transcriber."""
import torch
from pathlib import Path
from typing import Tuple, Optional, Any
from config.environment import WHISPER_AVAILABLE, FASTER_WHISPER_AVAILABLE
from config.logger import get_logger

logger = get_logger(__name__)

if WHISPER_AVAILABLE:
    import whisper

if FASTER_WHISPER_AVAILABLE:
    from faster_whisper import WhisperModel


class ModelManager:
    """Manages Whisper model loading, caching, and cleanup."""
    
    def __init__(self, environment: Any) -> None:
        """Initialize model manager.
        
        Args:
            environment: Environment instance with GPU detection.
        """
        self.environment = environment
        self.whisper_model: Optional[Any] = None
        self.faster_whisper_model: Optional[Any] = None
        
        # Track current model configuration for caching
        self.loaded_engine: Optional[str] = None
        self.loaded_model_size: Optional[str] = None
        self.loaded_compute_type: Optional[str] = None
    
    def is_model_loaded(self, engine: str, model_size: str, compute_type: str) -> bool:
        """Check if a model with the exact configuration is already loaded.
        
        This enables caching to avoid unnecessary model reloads.
        
        Args:
            engine: Engine type to check.
            model_size: Model size to check.
            compute_type: Compute type to check.
            
        Returns:
            True if a model with matching configuration is loaded, False otherwise.
        """
        # Resolve auto_gpu to actual engine for comparison
        actual_engine = self.environment.resolve_engine(engine)
        actual_loaded = self.environment.resolve_engine(self.loaded_engine) if self.loaded_engine else None
        
        # Check if all parameters match
        return (
            actual_engine == actual_loaded and
            model_size == self.loaded_model_size and
            compute_type == self.loaded_compute_type and
            self.get_active_model()[0] is not None  # Ensure a model is actually loaded
        )    
    def load_model(self, engine: str, model_size: str, compute_type: str) -> Tuple[bool, Optional[str]]:
        """Load transcription model with error handling and caching.
        
        If a model with the exact same configuration is already loaded,
        it will be reused instead of reloaded. This significantly improves 
        performance for sequential batch jobs with the same model.
        
        Args:
            engine: Engine type (auto_gpu, whisper_gpu, whisper_cpu, faster_whisper_gpu, faster_whisper_cpu).
            model_size: Model size (tiny, base, small, medium, large-v3, turbo).
            compute_type: Compute precision (float16, int8, int8_float16).
            
        Returns:
            Tuple of (success, error_message). success is True if loaded successfully,
            False otherwise. error_message is None on success, or descriptive error string on failure.
        """
        # Check if model is already loaded with same configuration (use cache)
        if self.is_model_loaded(engine, model_size, compute_type):
            logger.info(f"Reusing cached model: {model_size} ({engine})")
            return True, None
        
        try:
            # Resolve auto_gpu to specific engine
            actual_engine = self.environment.resolve_engine(engine)
            
            # Load appropriate model
            if actual_engine.startswith("faster_whisper"):
                if not FASTER_WHISPER_AVAILABLE:
                    return False, "Faster-Whisper library not installed. Install with: pip install faster-whisper"
                
                device = "cuda" if actual_engine.endswith("_gpu") and self.environment.gpu_available else "cpu"
                try:
                    self.faster_whisper_model = WhisperModel(
                        model_size, device=device, compute_type=compute_type)
                    logger.info(f"Successfully loaded Faster-Whisper {model_size} model on {device}")
                    # Update configuration tracking
                    self.loaded_engine = engine
                    self.loaded_model_size = model_size
                    self.loaded_compute_type = compute_type
                except torch.cuda.OutOfMemoryError:
                    return False, f"GPU out of memory. Try using a smaller model size or CPU mode."
                except RuntimeError as e:
                    if "CUDA" in str(e) or "cuda" in str(e):
                        return False, f"CUDA error: {str(e)}. Try using CPU mode instead."
                    raise
                    
            elif actual_engine.startswith("whisper"):
                if not WHISPER_AVAILABLE:
                    return False, "Whisper library not installed. Install with: pip install openai-whisper"
                
                device = self.environment.device if actual_engine.endswith("_gpu") else "cpu"
                try:
                    self.whisper_model = whisper.load_model(model_size, device=device)
                    logger.info(f"Successfully loaded Whisper {model_size} model on {device}")
                    # Update configuration tracking
                    self.loaded_engine = engine
                    self.loaded_model_size = model_size
                    self.loaded_compute_type = compute_type
                except torch.cuda.OutOfMemoryError:
                    return False, f"GPU out of memory. Try using a smaller model size or CPU mode."
                except RuntimeError as e:
                    if "CUDA" in str(e) or "cuda" in str(e):
                        return False, f"CUDA error: {str(e)}. Try using CPU mode instead."
                    raise
            else:
                return False, f"Unknown engine type: {actual_engine}"
                
            return True, None
            
        except FileNotFoundError as e:
            error_msg = f"Model file not found: {str(e)}. The model may not be downloaded."
            logger.error(error_msg)
            return False, error_msg
            
        except PermissionError as e:
            error_msg = f"Permission denied accessing model cache: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except OSError as e:
            error_msg = f"OS error loading model: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error loading model: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def cleanup_model(self) -> None:
        """Clean up models and free GPU memory."""
        if self.faster_whisper_model:
            del self.faster_whisper_model
            self.faster_whisper_model = None
        if self.whisper_model:
            del self.whisper_model
            self.whisper_model = None
        # Reset configuration tracking
        self.loaded_engine = None
        self.loaded_model_size = None
        self.loaded_compute_type = None
        if self.environment.gpu_available:
            torch.cuda.empty_cache()
    
    def check_model_downloaded(self, model_size: str) -> Tuple[bool, bool]:
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
    
    def download_model(self, model_size: str, engine: str, compute_type: str) -> None:
        """Download a specific model.
        
        Args:
            model_size: Model size to download.
            engine: Engine type.
            compute_type: Compute precision.
        """
        # Resolve auto_gpu
        actual_engine = self.environment.resolve_engine(engine)
        
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
    
    def get_active_model(self) -> Tuple[Optional[Any], Optional[str]]:
        """Get the currently active model.
        
        Returns:
            Tuple of (model, model_type) where model_type is 'whisper' or 'faster_whisper'.
        """
        if self.faster_whisper_model:
            return self.faster_whisper_model, 'faster_whisper'
        elif self.whisper_model:
            return self.whisper_model, 'whisper'
        return None, None

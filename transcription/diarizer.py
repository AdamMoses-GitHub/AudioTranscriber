"""Speaker diarization module for Audio Transcriber."""
import torch
import av
import numpy as np
import os
import gc
import tempfile
import traceback
import warnings

# Suppress benign HuggingFace symlink warning on Windows (no Developer Mode)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from typing import Optional, List, Tuple
from config.environment import PYANNOTE_AVAILABLE
from config.constants import (
    DEFAULT_DIARIZATION_MODEL,
    MIN_SPEAKERS,
    MAX_SPEAKERS,
    SPEAKER_LABEL_FORMAT
)
from config.logger import get_logger

logger = get_logger(__name__)

if PYANNOTE_AVAILABLE:
    from pyannote.audio import Pipeline
    try:
        from huggingface_hub import login as hf_login
    except ImportError:
        hf_login = None


class Diarizer:
    """Handles speaker diarization using pyannote.audio."""
    
    def __init__(self, environment):
        """Initialize diarizer.
        
        Args:
            environment: Environment instance for GPU detection.
        """
        self.environment = environment
        self.pipeline = None
        self.hf_token = None
        self.model_name = DEFAULT_DIARIZATION_MODEL
        self.device = None
        
        if not PYANNOTE_AVAILABLE:
            logger.warning("pyannote.audio not available. Speaker diarization disabled.")
    
    def is_available(self) -> bool:
        """Check if diarization is available.
        
        Returns:
            True if pyannote.audio is installed, False otherwise.
        """
        return PYANNOTE_AVAILABLE
    
    def load_pipeline(self, hf_token: str, model_name: Optional[str] = None, 
                     whisper_loaded: bool = False) -> bool:
        """Load pyannote pipeline with authentication.
        
        Args:
            hf_token: Hugging Face authentication token.
            model_name: Model name to load (default: pyannote/speaker-diarization-3.1).
            whisper_loaded: Whether Whisper model is currently in GPU memory.
            
        Returns:
            True if pipeline loaded successfully, False otherwise.
        """
        if not PYANNOTE_AVAILABLE:
            logger.error("Cannot load pipeline: pyannote.audio not installed")
            return False
        
        try:
            if model_name:
                self.model_name = model_name
            
            self.hf_token = hf_token
            
            # Determine device (cuda or cpu)
            self.device = torch.device(self.environment.get_diarization_device(whisper_loaded))
            
            logger.info(f"Loading diarization pipeline: {self.model_name}")
            logger.info(f"Using device: {self.device}")
            
            # Authenticate with HuggingFace Hub
            if hf_login:
                logger.debug("Authenticating with HuggingFace Hub")
                hf_login(token=hf_token, add_to_git_credential=False)
            else:
                # Fallback to environment variable
                os.environ['HUGGINGFACE_TOKEN'] = hf_token
                os.environ['HF_TOKEN'] = hf_token
            
            # Load pipeline from Hugging Face (token is handled by login/env var)
            self.pipeline = Pipeline.from_pretrained(self.model_name)
            
            # Move to appropriate device
            self.pipeline.to(self.device)
            
            logger.info("Diarization pipeline loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading diarization pipeline: {e}")
            self.pipeline = None
            return False
    
    def diarize(self, audio_file: str, num_speakers: Optional[int] = None) -> List[Tuple[float, float, str]]:
        """Run speaker diarization on audio file.
        
        Args:
            audio_file: Path to audio file.
            num_speakers: Number of expected speakers (None = auto-detect).
            
        Returns:
            List of tuples (start_time, end_time, speaker_label).
            Example: [(0.0, 15.3, "SPEAKER_00"), (15.3, 32.1, "SPEAKER_01"), ...]
            
        Raises:
            RuntimeError: If pipeline not loaded or diarization fails.
        """
        if not self.pipeline:
            raise RuntimeError(
                "Diarization pipeline not loaded. Call load_pipeline() first."
            )
        
        try:
            logger.info(f"Starting diarization: {audio_file}")
            
            # Validate num_speakers
            if num_speakers is not None:
                if num_speakers < MIN_SPEAKERS or num_speakers > MAX_SPEAKERS:
                    logger.warning(
                        f"num_speakers {num_speakers} out of range [{MIN_SPEAKERS}, {MAX_SPEAKERS}]. "
                        f"Using auto-detect."
                    )
                    num_speakers = None
            
            # Load audio using av library (avoids torchcodec issues)
            logger.info("Loading audio file...")
            container = av.open(audio_file)
            audio_stream = container.streams.audio[0]
            sample_rate = audio_stream.rate

            temp_pcm_path = None
            mmap_audio = None
            try:
                # Stream frames to a temp raw PCM file (float32 interleaved) to avoid
                # keeping all decoded frame arrays in memory at once.
                channels = None
                total_samples = 0
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pcm') as pcm_file:
                    temp_pcm_path = pcm_file.name
                    for frame in container.decode(audio=0):
                        frame_array = frame.to_ndarray()
                        if frame_array.ndim == 1:
                            frame_array = frame_array[np.newaxis, :]

                        if channels is None:
                            channels = frame_array.shape[0]

                        if frame_array.shape[0] != channels:
                            # Normalize channel count by truncating to the first detected layout.
                            frame_array = frame_array[:channels, :]

                        # Normalize integer PCM to [-1, 1] float32.
                        if np.issubdtype(frame_array.dtype, np.integer):
                            max_val = float(np.iinfo(frame_array.dtype).max or 1)
                            frame_array = frame_array.astype(np.float32) / max_val
                        else:
                            frame_array = frame_array.astype(np.float32, copy=False)

                        samples_in_frame = int(frame_array.shape[1])
                        if samples_in_frame <= 0:
                            continue

                        interleaved = np.ascontiguousarray(frame_array.T)
                        interleaved.tofile(pcm_file)
                        total_samples += samples_in_frame

                if channels is None or total_samples <= 0:
                    raise RuntimeError("No audio data found in file")

                # Memory-map the interleaved PCM and convert once to channel-first tensor.
                mmap_audio = np.memmap(
                    temp_pcm_path,
                    dtype=np.float32,
                    mode='r+',
                    shape=(total_samples, channels)
                )
                waveform = torch.from_numpy(mmap_audio).transpose(0, 1)
            finally:
                container.close()
            
            # Create audio dict for pyannote.audio
            audio = {
                'waveform': waveform,
                'sample_rate': sample_rate
            }
            logger.info(
                "Prepared diarization audio: waveform_shape=%s dtype=%s sample_rate=%s device=%s",
                tuple(waveform.shape),
                waveform.dtype,
                sample_rate,
                self.device,
            )
            
            # Run diarization (suppress known informational TF32 reproducibility warning noise).
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    'ignore',
                    message=r'.*TensorFloat-32 \(TF32\) has been disabled.*',
                    category=UserWarning,
                    module=r'pyannote\.audio\.utils\.reproducibility'
                )

                if num_speakers:
                    logger.info(f"Diarizing with {num_speakers} speakers")
                    logger.info("Invoking pyannote pipeline with explicit speaker count")
                    diarization = self.pipeline(audio, num_speakers=num_speakers)
                else:
                    # Auto-detect, but BOUND the search with min/max speakers.
                    # Without an upper bound, pyannote over-segments long (multi-hour)
                    # recordings into dozens of phantom speakers, which both ruins
                    # label quality and inflates host-RAM clustering structures.
                    logger.info(
                        "Diarizing with auto-detect speakers (bounded: min=%s max=%s)",
                        MIN_SPEAKERS, MAX_SPEAKERS
                    )
                    diarization = self.pipeline(
                        audio,
                        min_speakers=MIN_SPEAKERS,
                        max_speakers=MAX_SPEAKERS
                    )

            logger.info(
                "Pyannote pipeline returned: type=%s attrs=%s",
                type(diarization).__name__,
                [name for name in dir(diarization) if not name.startswith('__')][:20],
            )
            
            # Convert diarization result to list of tuples
            # pyannote.audio 4.0+ returns a DiarizeOutput object
            timeline = []
            speaker_map = {}  # Map pyannote labels to our format
            speaker_count = 0
            
            # Extract the annotation from DiarizeOutput (v4) or use directly (v3)
            if hasattr(diarization, 'speaker_diarization'):
                # pyannote.audio 4.0+ format - extract the annotation
                annotation = diarization.speaker_diarization
            else:
                # pyannote.audio 3.x format - already an annotation
                annotation = diarization
            
            # Iterate through the annotation
            for turn, _, speaker in annotation.itertracks(yield_label=True):
                # Map speaker to consistent label format
                if speaker not in speaker_map:
                    speaker_map[speaker] = SPEAKER_LABEL_FORMAT.format(speaker_count)
                    speaker_count += 1
                
                speaker_label = speaker_map[speaker]
                timeline.append((turn.start, turn.end, speaker_label))
            
            logger.info(f"Diarization complete: {speaker_count} speakers detected, {len(timeline)} segments")
            return timeline
            
        except Exception as e:
            logger.error("Error during diarization: %s [%s]", e, type(e).__name__)
            logger.debug("Diarization traceback:\n%s", traceback.format_exc())
            # Preserve the original exception type name so callers can classify
            # the failure accurately instead of masking it behind a generic label.
            raise RuntimeError(f"Diarization failed: {type(e).__name__}: {e}")
        finally:
            # Critical: release both GPU and HOST memory between files. Long
            # multi-hour recordings allocate large host-side clustering tensors
            # inside pyannote; without an explicit gc pass these accumulate
            # across a batch and eventually exhaust system RAM.
            try:
                if 'diarization' in locals():
                    del diarization
                if 'annotation' in locals():
                    del annotation
                if 'waveform' in locals() and waveform is not None:
                    del waveform
                if 'audio' in locals():
                    del audio
            except Exception:
                pass

            if mmap_audio is not None:
                try:
                    mmap_audio._mmap.close()
                except Exception:
                    pass
            if temp_pcm_path and os.path.exists(temp_pcm_path):
                try:
                    os.remove(temp_pcm_path)
                except OSError:
                    pass

            # Force host-side garbage collection, then clear the GPU cache.
            try:
                gc.collect()
                if self.device and self.device.type == "cuda":
                    torch.cuda.empty_cache()
            except Exception:
                pass
    
    def cleanup(self):
        """Free GPU memory used by diarization pipeline."""
        if self.pipeline:
            logger.info("Cleaning up diarization pipeline")
            try:
                # Delete pipeline
                del self.pipeline
                self.pipeline = None
                
                # Clear GPU cache if using CUDA
                if self.device and self.device.type == "cuda":
                    torch.cuda.empty_cache()
                    logger.info("GPU memory cleared")
                    
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
    
    def validate_token(self, hf_token: str) -> Tuple[bool, str]:
        """Validate Hugging Face token by attempting to access the model.
        
        Args:
            hf_token: Hugging Face authentication token.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        if not PYANNOTE_AVAILABLE:
            return False, "pyannote.audio not installed"
        
        if not hf_token or not hf_token.strip():
            return False, "Token is empty"
        
        try:
            # Try to access the model (doesn't download, just checks access)
            from huggingface_hub import hf_hub_download
            
            # Check if we can access the model
            hf_hub_download(
                repo_id=self.model_name,
                filename="config.yaml",
                token=hf_token,
                local_files_only=False
            )
            return True, "Token valid"
            
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                return False, "Invalid token or insufficient permissions"
            elif "403" in error_msg or "forbidden" in error_msg.lower():
                return False, "Access denied. Have you accepted the model license on Hugging Face?"
            elif "404" in error_msg:
                return False, "Model not found"
            else:
                return False, f"Validation error: {error_msg}"
    
    def get_device_info(self) -> str:
        """Get information about the device being used for diarization.
        
        Returns:
            Human-readable device information.
        """
        if not self.pipeline:
            device = self.environment.get_diarization_device(whisper_loaded=False)
            return f"Device: {device} (pipeline not loaded)"
        
        if self.device and self.device.type == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            return f"Device: CUDA ({gpu_name})"
        else:
            return "Device: CPU"

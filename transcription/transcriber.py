"""Transcriber for audio files."""
from config.environment import WHISPER_AVAILABLE, FASTER_WHISPER_AVAILABLE
from .metadata_extractor import MetadataExtractor


class Transcriber:
    """Handles audio transcription using Whisper models."""
    
    def __init__(self, model_manager, environment):
        """Initialize transcriber.
        
        Args:
            model_manager: ModelManager instance.
            environment: Environment instance.
        """
        self.model_manager = model_manager
        self.environment = environment
        self.metadata_extractor = MetadataExtractor()
    
    def transcribe(self, audio_file, engine):
        """Transcribe audio file (simple version).
        
        Args:
            audio_file: Path to audio file.
            engine: Engine type being used.
            
        Returns:
            Transcribed text string.
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
        
        # Get active model
        model, model_type = self.model_manager.get_active_model()
        
        if not model:
            raise Exception("No model loaded")
        
        # Transcribe based on model type
        if model_type == 'faster_whisper':
            segments, info = model.transcribe(audio_file, beam_size=5, vad_filter=True)
            text = ""
            for segment in segments:
                text += segment.text + " "
            return text.strip()
        elif model_type == 'whisper':
            result = model.transcribe(audio_file)
            return result["text"]
        else:
            raise Exception("Unknown model type")
    
    def transcribe_with_metadata(self, audio_file, engine):
        """Transcribe audio file and return comprehensive metadata.
        
        Args:
            audio_file: Path to audio file.
            engine: Engine type being used.
            
        Returns:
            Dictionary with text, language, duration, confidence, and audio metadata.
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
        
        # Get active model
        model, model_type = self.model_manager.get_active_model()
        
        if not model:
            raise Exception("No model loaded")
        
        # Get audio metadata
        audio_metadata = self.metadata_extractor.get_audio_metadata(audio_file)
        
        # Transcribe based on model type
        if model_type == 'faster_whisper':
            segments, info = model.transcribe(audio_file, beam_size=5, vad_filter=True)
            text = ""
            total_confidence = 0
            segment_count = 0
            
            for segment in segments:
                text += segment.text + " "
                if hasattr(segment, 'avg_logprob'):
                    total_confidence += segment.avg_logprob
                    segment_count += 1
            
            avg_confidence = total_confidence / segment_count if segment_count > 0 else None
            
            return {
                'text': text.strip(),
                'language': info.language if hasattr(info, 'language') else 'Unknown',
                'duration': info.duration if hasattr(info, 'duration') else 0,
                'avg_logprob': avg_confidence,
                'audio_metadata': audio_metadata
            }
        elif model_type == 'whisper':
            result = model.transcribe(audio_file)
            
            # Calculate average confidence from segments if available
            avg_confidence = None
            if 'segments' in result and len(result['segments']) > 0:
                confidences = [seg.get('avg_logprob', 0) for seg in result['segments']]
                avg_confidence = sum(confidences) / len(confidences) if confidences else None
            
            return {
                'text': result['text'],
                'language': result.get('language', 'Unknown'),
                'duration': result.get('duration', 0),
                'avg_logprob': avg_confidence,
                'audio_metadata': audio_metadata
            }
        else:
            raise Exception("Unknown model type")

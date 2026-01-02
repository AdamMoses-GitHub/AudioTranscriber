"""Transcriber for audio files."""
from config.environment import WHISPER_AVAILABLE, FASTER_WHISPER_AVAILABLE
from .metadata_extractor import MetadataExtractor
from utilities.format_utils import FormatUtils


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
    
    def transcribe(self, audio_file, engine, options=None):
        """Transcribe audio file (simple version).
        
        Args:
            audio_file: Path to audio file.
            engine: Engine type being used.
            options: Optional dict with timestamp settings (timestamps_enabled, timestamp_format, timestamp_interval).
            
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
            raise RuntimeError(
                "No model loaded. Please select a model in Model Configuration tab "
                "and ensure it downloaded successfully."
            )
        
        # Transcribe based on model type
        if model_type == 'faster_whisper':
            segments, info = model.transcribe(audio_file, beam_size=5, vad_filter=True)
            
            # Collect segments with timing data
            segment_list = []
            for segment in segments:
                segment_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text
                })
            
            # Apply timestamps if requested
            if options and options.get('timestamps_enabled', False):
                return FormatUtils.insert_interval_timestamps(
                    segment_list,
                    options.get('timestamp_interval', 30),
                    options.get('timestamp_format', 'HH:MM:SS')
                )
            else:
                # Concatenate text without timestamps using join() for efficiency
                text = " ".join(seg['text'].strip() for seg in segment_list if seg['text'].strip())
                return text
                
        elif model_type == 'whisper':
            result = model.transcribe(audio_file)
            
            # Apply timestamps if requested
            if options and options.get('timestamps_enabled', False) and 'segments' in result:
                segment_list = []
                for seg in result['segments']:
                    segment_list.append({
                        'start': seg.get('start', 0),
                        'end': seg.get('end', 0),
                        'text': seg.get('text', '')
                    })
                return FormatUtils.insert_interval_timestamps(
                    segment_list,
                    options.get('timestamp_interval', 30),
                    options.get('timestamp_format', 'HH:MM:SS')
                )
            else:
                return result["text"]
        else:
            raise Exception("Unknown model type")
    
    def transcribe_with_metadata(self, audio_file, engine, options=None):
        """Transcribe audio file and return comprehensive metadata.
        
        Args:
            audio_file: Path to audio file.
            engine: Engine type being used.
            options: Optional dict with timestamp settings (timestamps_enabled, timestamp_format, timestamp_interval).
            
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
            raise RuntimeError(
                "No model loaded. Please select a model in Model Configuration tab "
                "and ensure it downloaded successfully."
            )
        
        # Get audio metadata
        audio_metadata = self.metadata_extractor.get_audio_metadata(audio_file)
        
        # Transcribe based on model type
        if model_type == 'faster_whisper':
            segments, info = model.transcribe(audio_file, beam_size=5, vad_filter=True)
            
            # Collect segments with timing data
            segment_list = []
            total_confidence = 0
            segment_count = 0
            
            for segment in segments:
                segment_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text
                })
                if hasattr(segment, 'avg_logprob'):
                    total_confidence += segment.avg_logprob
                    segment_count += 1
            
            avg_confidence = total_confidence / segment_count if segment_count > 0 else None
            
            # Apply timestamps if requested
            if options and options.get('timestamps_enabled', False):
                text = FormatUtils.insert_interval_timestamps(
                    segment_list,
                    options.get('timestamp_interval', 30),
                    options.get('timestamp_format', 'HH:MM:SS')
                )
            else:
                # Concatenate text without timestamps
                text = ""
                for seg in segment_list:
                    text += seg['text'] + " "
                text = text.strip()
            
            return {
                'text': text,
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
            
            # Apply timestamps if requested
            if options and options.get('timestamps_enabled', False) and 'segments' in result:
                segment_list = []
                for seg in result['segments']:
                    segment_list.append({
                        'start': seg.get('start', 0),
                        'end': seg.get('end', 0),
                        'text': seg.get('text', '')
                    })
                text = FormatUtils.insert_interval_timestamps(
                    segment_list,
                    options.get('timestamp_interval', 30),
                    options.get('timestamp_format', 'HH:MM:SS')
                )
            else:
                # Concatenate text without timestamps using join() for efficiency
                text = " ".join(seg['text'].strip() for seg in segment_list if seg['text'].strip())
            
            return {
                'text': text,
                'language': result.get('language', 'Unknown'),
                'duration': result.get('duration', 0),
                'avg_logprob': avg_confidence,
                'audio_metadata': audio_metadata
            }
        else:
            raise Exception("Unknown model type")

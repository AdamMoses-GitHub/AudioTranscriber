"""Transcriber for audio files."""
from typing import Optional, List, Tuple, Dict, Any
from config.environment import WHISPER_AVAILABLE, FASTER_WHISPER_AVAILABLE
from .metadata_extractor import MetadataExtractor
from utilities.format_utils import FormatUtils
from config.logger import get_logger

logger = get_logger(__name__)


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
        actual_engine = self.environment.resolve_engine(engine)
        
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
        actual_engine = self.environment.resolve_engine(engine)
        
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
                text = result.get('text', '')
            
            return {
                'text': text,
                'language': result.get('language', 'Unknown'),
                'duration': result.get('duration', 0),
                'avg_logprob': avg_confidence,
                'audio_metadata': audio_metadata
            }
        else:
            raise Exception("Unknown model type")
    
    def transcribe_with_diarization(self, audio_file: str, engine: str, diarizer: Any, 
                                     num_speakers: Optional[int] = None, options: Optional[Dict] = None) -> Dict:
        """Transcribe audio file with speaker diarization.
        
        Args:
            audio_file: Path to audio file.
            engine: Engine type being used.
            diarizer: Diarizer instance (already loaded with pipeline).
            num_speakers: Number of expected speakers (None = auto-detect).
            options: Optional dict with timestamp settings.
            
        Returns:
            Dictionary with text (speaker-labeled), language, duration, confidence, 
            audio metadata, and speaker timeline.
        """
        logger.info(f"Starting transcription with diarization: {audio_file}")
        
        # Step 1: Run diarization to get speaker timeline
        logger.info("Step 1/3: Running speaker diarization...")
        speaker_timeline = diarizer.diarize(audio_file, num_speakers)
        
        # Step 2: Transcribe audio with timestamps (reuse existing code!)
        logger.info("Step 2/3: Running speech-to-text transcription...")
        # Force timestamps to be captured in segments (we'll format later)
        transcribe_options = options.copy() if options else {}
        transcribe_options['timestamps_enabled'] = False  # We'll handle formatting with speakers
        
        result = self.transcribe_with_metadata(audio_file, engine, transcribe_options)
        
        # Step 3: Get segments with timestamps for merging
        logger.info("Step 3/3: Merging speaker labels with transcript...")
        segments = self._extract_segments_from_transcription(audio_file, engine)
        
        # Merge speaker labels with transcript segments
        labeled_text = self._merge_speakers_with_transcript(speaker_timeline, segments)
        
        # Update result with speaker-labeled text
        result['text'] = labeled_text
        result['speaker_timeline'] = speaker_timeline
        result['num_speakers'] = len(set(label for _, _, label in speaker_timeline))
        
        logger.info(f"Diarization complete: {result['num_speakers']} speakers detected")
        return result
    
    def _extract_segments_from_transcription(self, audio_file: str, engine: str) -> List[Dict]:
        """Extract segments with timestamps from transcription.
        
        Args:
            audio_file: Path to audio file.
            engine: Engine type being used.
            
        Returns:
            List of segments with 'start', 'end', and 'text' keys.
        """
        # Resolve auto_gpu
        actual_engine = self.environment.resolve_engine(engine)
        
        # Get active model
        model, model_type = self.model_manager.get_active_model()
        
        if not model:
            raise RuntimeError("No model loaded")
        
        segment_list = []
        
        if model_type == 'faster_whisper':
            segments, info = model.transcribe(audio_file, beam_size=5, vad_filter=True)
            for segment in segments:
                segment_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text
                })
        elif model_type == 'whisper':
            result = model.transcribe(audio_file)
            if 'segments' in result:
                for seg in result['segments']:
                    segment_list.append({
                        'start': seg.get('start', 0),
                        'end': seg.get('end', 0),
                        'text': seg.get('text', '')
                    })
        
        return segment_list
    
    def _merge_speakers_with_transcript(self, speaker_timeline: List[Tuple[float, float, str]], 
                                        segments: List[Dict]) -> str:
        """Merge speaker labels with transcript segments.
        
        Matches transcript segments to speaker timeline by timestamp overlap.
        
        Args:
            speaker_timeline: List of (start, end, speaker_label) tuples.
            segments: List of dicts with 'start', 'end', 'text' keys.
            
        Returns:
            Formatted text with speaker labels (e.g., "SPEAKER_00: text\nSPEAKER_01: text").
        """
        if not segments:
            return ""
        
        # Build output with speaker labels
        output_lines = []
        current_speaker = None
        current_text = []
        
        for segment in segments:
            segment_start = segment['start']
            segment_end = segment['end']
            segment_text = segment['text'].strip()
            
            if not segment_text:
                continue
            
            # Find the speaker for this segment (based on maximum overlap)
            speaker = self._find_speaker_for_segment(segment_start, segment_end, speaker_timeline)
            
            # If speaker changed, flush current text and start new line
            if speaker != current_speaker:
                if current_text:
                    # Write previous speaker's text
                    output_lines.append(f"{current_speaker}: {' '.join(current_text)}")
                    current_text = []
                current_speaker = speaker
            
            # Add text to current speaker's buffer
            current_text.append(segment_text)
        
        # Flush remaining text
        if current_text and current_speaker:
            output_lines.append(f"{current_speaker}: {' '.join(current_text)}")
        
        return "\n\n".join(output_lines)
    
    def _find_speaker_for_segment(self, segment_start: float, segment_end: float, 
                                   speaker_timeline: List[Tuple[float, float, str]]) -> str:
        """Find the speaker for a transcript segment based on timestamp overlap.
        
        Args:
            segment_start: Segment start time in seconds.
            segment_end: Segment end time in seconds.
            speaker_timeline: List of (start, end, speaker_label) tuples.
            
        Returns:
            Speaker label with maximum overlap, or "UNKNOWN" if no overlap found.
        """
        max_overlap = 0
        best_speaker = "UNKNOWN"
        
        for start, end, speaker in speaker_timeline:
            # Calculate overlap between segment and speaker turn
            overlap_start = max(segment_start, start)
            overlap_end = min(segment_end, end)
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = speaker
        
        return best_speaker

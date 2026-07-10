"""Transcriber for audio files."""
import time
from typing import Optional, List, Tuple, Dict, Any, Callable
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
    
    def _normalize_segments(self, model, model_type, audio_file):
        """Normalize segments from model output into standard format.
        
        Handles both faster_whisper and whisper model output formats,
        converting them to a uniform list of dicts with 'start', 'end', 'text' keys.
        
        Args:
            model: The loaded model instance.
            model_type: Either 'faster_whisper' or 'whisper'.
            audio_file: Path to audio file (required for model validation).
            
        Returns:
            Tuple of (segment_list, info, avg_confidence) where info is model metadata (duration, language, etc).
                segment_list: List of dicts with 'start', 'end', 'text' keys.
                info: Model-specific info object containing duration and language.
                avg_confidence: Average segment confidence when available, otherwise None.
        """
        segment_list = []
        info = None
        avg_confidence = None
        
        if model_type == 'faster_whisper':
            segments, info = model.transcribe(audio_file, beam_size=5, vad_filter=True)
            total_confidence = 0.0
            segment_count = 0
            for segment in segments:
                segment_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text
                })
                segment_confidence = getattr(segment, 'avg_logprob', None)
                if segment_confidence is not None:
                    total_confidence += float(segment_confidence)
                    segment_count += 1
            if segment_count > 0:
                avg_confidence = total_confidence / segment_count
        elif model_type == 'whisper':
            result = model.transcribe(audio_file)
            info = result  # Store the entire result for language and duration access
            
            if 'segments' in result:
                for seg in result['segments']:
                    segment_list.append({
                        'start': seg.get('start', 0),
                        'end': seg.get('end', 0),
                        'text': seg.get('text', '')
                    })
                confidences = [seg.get('avg_logprob') for seg in result['segments'] if seg.get('avg_logprob') is not None]
                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        return segment_list, info, avg_confidence
    
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
        
        # Normalize segments from model output
        segment_list, info, _ = self._normalize_segments(model, model_type, audio_file)
        
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
    
    def transcribe_with_metadata(self, audio_file, engine, options=None, progress_callback=None):
        """Transcribe audio file and return comprehensive metadata.
        
        Args:
            audio_file: Path to audio file.
            engine: Engine type being used.
            options: Optional dict with timestamp settings (timestamps_enabled, timestamp_format, timestamp_interval).
            progress_callback: Optional callback(progress, speed_factor, eta_seconds, current_position) for progress updates.
            
        Returns:
            Dictionary with text, language, duration, confidence, and audio metadata.
        """
        start_time = time.time()
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
        
        # Normalize segments from model output
        segment_list, info, avg_confidence = self._normalize_segments(model, model_type, audio_file)
        
        # Extract metadata based on model type
        if model_type == 'faster_whisper':
            language = info.language if hasattr(info, 'language') else 'Unknown'
            duration = info.duration if hasattr(info, 'duration') else 0
        elif model_type == 'whisper':
            language = info.get('language', 'Unknown') if isinstance(info, dict) else 'Unknown'
            duration = info.get('duration', 0) if isinstance(info, dict) else 0
        else:
            language = 'Unknown'
            duration = 0
            avg_confidence = None
        
        # Report progress if callback provided.
        # Throttle callback frequency to reduce UI update overhead on long files.
        if progress_callback and duration > 0 and segment_list:
            report_every = max(1, len(segment_list) // 100)
            for i, segment in enumerate(segment_list):
                is_last = (i == len(segment_list) - 1)
                if not is_last and (i % report_every) != 0:
                    continue

                elapsed_time = time.time() - start_time
                current_position = segment['end']
                progress = min(current_position / duration, 1.0)

                # Calculate speed factor (how much faster than realtime)
                speed_factor = current_position / elapsed_time if elapsed_time > 0 else 0

                # Estimate time remaining
                remaining_audio = duration - current_position
                eta_seconds = remaining_audio / speed_factor if speed_factor > 0 else None

                progress_callback(progress, speed_factor, eta_seconds, current_position)
        
        # Apply timestamps if requested
        if options and options.get('timestamps_enabled', False):
            text = FormatUtils.insert_interval_timestamps(
                segment_list,
                options.get('timestamp_interval', 30),
                options.get('timestamp_format', 'HH:MM:SS')
            )
        else:
            # Concatenate text without timestamps using join() for efficiency.
            text = " ".join(seg['text'].strip() for seg in segment_list if seg['text'].strip())
        
        return {
            'text': text,
            'language': language,
            'duration': duration,
            'avg_logprob': avg_confidence,
            'audio_metadata': audio_metadata,
            'segments': segment_list
        }
    
    def transcribe_with_diarization(self, audio_file: str, engine: str, diarizer: Any, 
                                     num_speakers: Optional[int] = None, options: Optional[Dict] = None,
                                     progress_callback: Optional[Callable] = None) -> Dict:
        """Transcribe audio file with speaker diarization.
        
        Args:
            audio_file: Path to audio file.
            engine: Engine type being used.
            diarizer: Diarizer instance (already loaded with pipeline).
            num_speakers: Number of expected speakers (None = auto-detect).
            options: Optional dict with timestamp settings.
            progress_callback: Optional callback(progress, speed_factor, eta_seconds, current_position) for progress updates.
            
        Returns:
            Dictionary with text (speaker-labeled), language, duration, confidence, 
            audio metadata, and speaker timeline.
        """
        logger.info(f"Starting transcription with diarization: {audio_file}")

        fallback_to_plain = True if options is None else options.get('diarization_fallback_to_plain', True)
        
        # Step 1: Run diarization to get speaker timeline
        logger.info("Step 1/3: Running speaker diarization...")
        try:
            speaker_timeline = diarizer.diarize(audio_file, num_speakers)
        except Exception as e:
            if not fallback_to_plain:
                raise

            logger.warning(
                "Diarization failed for %s. Falling back to plain transcription. Error: %s",
                audio_file,
                e
            )
            result = self.transcribe_with_metadata(audio_file, engine, options, progress_callback=progress_callback)
            result['speaker_timeline'] = []
            result['num_speakers'] = 0
            result['diarization_fallback'] = True
            result['diarization_error'] = str(e)
            return result
        
        # Step 2: Transcribe audio with timestamps (reuse existing code!)
        logger.info("Step 2/3: Running speech-to-text transcription...")
        # Get raw transcription data - we'll format timestamps with speakers in step 3
        transcribe_options = options.copy() if options else {}
        transcribe_options['timestamps_enabled'] = False  # Format timestamps with speakers in merge step
        transcribe_options['diarization_timestamp_mode'] = (
            options.get('diarization_timestamp_mode', 'speaker_turns') if options else 'speaker_turns'
        )
        
        result = self.transcribe_with_metadata(audio_file, engine, transcribe_options, progress_callback=progress_callback)
        
        # Step 3: Reuse already-transcribed segments for merging to avoid a second inference pass.
        logger.info("Step 3/3: Merging speaker labels with transcript...")
        segments = result.get('segments') or self._extract_segments_from_transcription(audio_file, engine)
        
        # Merge speaker labels with transcript segments (pass options for timestamp formatting)
        labeled_text = self._merge_speakers_with_transcript(speaker_timeline, segments, options)
        
        # Update result with speaker-labeled text
        result['text'] = labeled_text
        result['speaker_timeline'] = speaker_timeline
        result['num_speakers'] = len(set(label for _, _, label in speaker_timeline))
        result['diarization_fallback'] = False
        
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
        
        # Use the normalized segments method
        segment_list, info, _ = self._normalize_segments(model, model_type, audio_file)
        return segment_list
    
    def _merge_speakers_with_transcript(self, speaker_timeline: List[Tuple[float, float, str]], 
                                        segments: List[Dict], options: Optional[Dict] = None) -> str:
        """Merge speaker labels with transcript segments.
        
        Matches transcript segments to speaker timeline by timestamp overlap.
        
        Args:
            speaker_timeline: List of (start, end, speaker_label) tuples.
            segments: List of dicts with 'start', 'end', 'text' keys.
            options: Optional dict with timestamp settings (timestamps_enabled, timestamp_format, timestamp_interval).
            
        Returns:
            Formatted text with speaker labels (e.g., "SPEAKER_00: text\nSPEAKER_01: text").
            If timestamps enabled, includes timestamps at specified intervals.
        """
        if not segments:
            return ""
        
        # Check if timestamps should be included
        include_timestamps = options and options.get('timestamps_enabled', False)
        timestamp_mode = options.get('diarization_timestamp_mode', 'speaker_turns') if options else 'speaker_turns'
        timestamp_format = options.get('timestamp_format', 'HH:MM:SS') if options else 'HH:MM:SS'
        timestamp_interval = options.get('timestamp_interval', 30) if options else 30
        
        # Build output with speaker labels
        output_lines = []
        current_speaker = None
        current_text = []
        current_start_time = None
        last_timestamp_time = 0
        
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
                    text_line = ' '.join(current_text)
                    if include_timestamps and current_start_time is not None:
                        timestamp_str = FormatUtils.format_timestamp(current_start_time, timestamp_format)
                        output_lines.append(f"{timestamp_str} {current_speaker}: {text_line}")
                    else:
                        output_lines.append(f"{current_speaker}: {text_line}")
                    current_text = []
                current_speaker = speaker
                current_start_time = segment_start
                last_timestamp_time = segment_start
            
            # Check if we need to insert an interval timestamp for diarized output.
            elif (
                include_timestamps
                and timestamp_mode == 'interval'
                and (segment_start - last_timestamp_time) >= timestamp_interval
            ):
                # Flush current text with timestamp
                if current_text:
                    text_line = ' '.join(current_text)
                    timestamp_str = FormatUtils.format_timestamp(current_start_time, timestamp_format)
                    output_lines.append(f"{timestamp_str} {current_speaker}: {text_line}")
                    current_text = []
                    current_start_time = segment_start
                    last_timestamp_time = segment_start
            
            # Add text to current speaker's buffer
            current_text.append(segment_text)
        
        # Flush remaining text
        if current_text and current_speaker:
            text_line = ' '.join(current_text)
            if include_timestamps and current_start_time is not None:
                timestamp_str = FormatUtils.format_timestamp(current_start_time, timestamp_format)
                output_lines.append(f"{timestamp_str} {current_speaker}: {text_line}")
            else:
                output_lines.append(f"{current_speaker}: {text_line}")
        
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

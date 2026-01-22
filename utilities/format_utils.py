"""Formatting utilities for Audio Transcriber."""
from config.constants import SECONDS_PER_MINUTE, SECONDS_PER_HOUR, BYTES_PER_KB, BYTES_PER_MB


class FormatUtils:
    """Utilities for text and time formatting."""
    
    @staticmethod
    def extract_transcription_results(result):
        """Extract transcription results from transcriber output.
        
        Centralizes result parsing to handle both dict and string return types,
        providing default values for missing fields. Reduces code duplication
        across CLI, GUI, and batch processing modules.
        
        Args:
            result: Result from transcriber.transcribe_with_metadata(), which may be
                   a dict with full metadata or a string with just the transcribed text.
        
        Returns:
            Tuple of (text, language, duration, avg_confidence, audio_metadata)
        """
        if isinstance(result, dict):
            text = result.get('text', '')
            language = result.get('language', 'Unknown')
            duration = result.get('duration', 0)
            avg_confidence = result.get('avg_logprob', None)
            audio_metadata = result.get('audio_metadata', {})
        else:
            text = result
            language = 'Unknown'
            duration = 0
            avg_confidence = None
            audio_metadata = {}
        
        return text, language, duration, avg_confidence, audio_metadata
    
    @staticmethod
    def format_time(seconds):
        """Format time in seconds to human-readable format.
        
        Args:
            seconds: Time in seconds.
            
        Returns:
            Formatted time string.
        """
        if seconds == 0:
            return "0s"
        elif seconds < SECONDS_PER_MINUTE:
            return f"{seconds:.1f}s"
        elif seconds < SECONDS_PER_HOUR:
            minutes = int(seconds // SECONDS_PER_MINUTE)
            secs = seconds % SECONDS_PER_MINUTE
            return f"{minutes}m {secs:.1f}s"
        else:
            hours = int(seconds // SECONDS_PER_HOUR)
            minutes = int((seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE)
            secs = seconds % SECONDS_PER_MINUTE
            return f"{hours}h {minutes}m {secs:.0f}s"
    
    @staticmethod
    def format_text_with_line_breaks(text, max_chars=80):
        """Format text with line breaks based on character length, without breaking words.
        
        Args:
            text: The text to format.
            max_chars: Maximum characters per line (0 = no breaks).
        
        Returns:
            Formatted text with line breaks.
            
        Raises:
            TypeError: If text is not a string.
            ValueError: If max_chars is negative.
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be a string, got {type(text).__name__}")
        if max_chars < 0:
            raise ValueError("max_chars must be non-negative")
        if max_chars == 0:
            return text
            
        paragraphs = text.split('\n')
        formatted = []
        
        for para in paragraphs:
            if not para.strip():
                formatted.append("")
                continue
                
            words = para.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                if len(test_line) <= max_chars:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
                    
            # Add the last line
            if current_line:
                lines.append(current_line)
                
            formatted.append('\n'.join(lines))
            
        return '\n'.join(formatted)
    
    @staticmethod
    def format_file_size(size_bytes):
        """Format file size in bytes to human-readable format.
        
        Args:
            size_bytes: Size in bytes.
            
        Returns:
            Formatted size string.
        """
        size_mb = size_bytes / BYTES_PER_MB
        if size_mb < 1:
            return f"{size_bytes / BYTES_PER_KB:.1f} KB"
        elif size_mb < 1024:
            return f"{size_mb:.1f} MB"
        else:
            return f"{size_mb / 1024:.1f} GB"
    
    @staticmethod
    def format_timestamp(seconds, format_type='HH:MM:SS'):
        """Format seconds to timestamp string.
        
        Args:
            seconds: Time in seconds.
            format_type: Format type - 'HH:MM:SS', 'MM:SS', or 'timecode'.
            
        Returns:
            Formatted timestamp string.
        """
        hours = int(seconds // SECONDS_PER_HOUR)
        minutes = int((seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE)
        secs = int(seconds % SECONDS_PER_MINUTE)
        millis = int((seconds % 1) * 1000)
        
        if format_type == 'HH:MM:SS':
            return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"
        elif format_type == 'MM:SS':
            total_minutes = int(seconds // SECONDS_PER_MINUTE)
            return f"[{total_minutes:02d}:{secs:02d}]"
        elif format_type == 'timecode':
            return f"[{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}]"
        else:
            # Default to HH:MM:SS
            return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"
    
    @staticmethod
    def insert_interval_timestamps(segments, interval_seconds, format_type='HH:MM:SS'):
        """Insert timestamps at regular intervals into transcribed text.
        
        Args:
            segments: List of segment dictionaries with 'start', 'end', and 'text' keys.
            interval_seconds: Interval in seconds for timestamp insertion.
            format_type: Format type for timestamps.
            
        Returns:
            Formatted text with timestamps at specified intervals.
        """
        if not segments:
            return ""
        
        # Start with timestamp at 0
        result = []
        result.append(FormatUtils.format_timestamp(0, format_type))
        
        current_interval = interval_seconds
        current_text = []
        
        for segment in segments:
            segment_start = segment.get('start', 0)
            segment_end = segment.get('end', 0)
            segment_text = segment.get('text', '').strip()
            
            if not segment_text:
                continue
            
            # Check if we need to insert a timestamp
            if segment_start >= current_interval:
                # Add accumulated text before timestamp
                if current_text:
                    result.append(' '.join(current_text))
                    current_text = []
                
                # Insert timestamp(s) for all passed intervals
                while current_interval <= segment_start:
                    result.append(FormatUtils.format_timestamp(current_interval, format_type))
                    current_interval += interval_seconds
            
            # Add segment text
            current_text.append(segment_text)
        
        # Add any remaining text
        if current_text:
            result.append(' '.join(current_text))
        
        # Join with newlines so each timestamp is on its own line
        return '\n'.join(result)
    
    @staticmethod
    def build_transcript_metadata(file_name: str, audio_metadata: dict, duration: float, 
                                   process_time: float, engine: str, model: str, 
                                   compute_type: str, language: str, 
                                   avg_confidence: float = None, detected_date = None, 
                                   day_of_week: str = None) -> str:
        """Build comprehensive metadata header for transcript files.
        
        Centralizes the common metadata formatting logic used across transcriber
        and batch processor to ensure consistency and reduce code duplication.
        
        Args:
            file_name: Name of the audio file.
            audio_metadata: Dictionary with audio metadata (sample_rate, channels, etc).
            duration: Audio duration in seconds.
            process_time: Transcription processing time in seconds.
            engine: Engine used for transcription.
            model: Model name used.
            compute_type: Compute precision used.
            language: Detected language.
            avg_confidence: Average confidence score (optional).
            detected_date: Detected date from filename (optional, datetime object).
            day_of_week: Detected day of week (optional).
            
        Returns:
            Formatted metadata header string.
        """
        from utilities.audio_utils import AudioUtils
        from config.constants import BYTES_PER_MB
        import time
        import os
        
        lines = []
        lines.append(f"Transcript of: {file_name}\n")
        
        if detected_date:
            lines.append(f"Recording Date: {detected_date.strftime('%Y-%m-%d')} ({day_of_week})\n")
        
        lines.append(f"Transcribed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("\n--- TRANSCRIPTION METADATA ---\n")
        
        # File size
        file_size_mb = audio_metadata.get('file_size_bytes', 0) / BYTES_PER_MB
        lines.append(f"File Size:         {file_size_mb:.2f} MB\n")
        
        # Audio format information
        audio_info = AudioUtils.format_audio_info(audio_metadata)
        if audio_info != "Unknown":
            lines.append(f"Audio Format:      {audio_info}\n")
        
        # MP3 tag information if available
        mp3_tags = AudioUtils.format_mp3_tags(audio_metadata)
        if mp3_tags:
            lines.append(f"MP3 Tags:\n{mp3_tags}\n")
        
        # Duration and processing time
        if duration > 0:
            lines.append(f"Duration:          {FormatUtils.format_time(duration)}\n")
        lines.append(f"Processing Time:   {FormatUtils.format_time(process_time)}\n")
        
        # Speed ratio
        if duration > 0 and process_time > 0:
            speed_ratio = duration / process_time
            lines.append(f"Speed:             {speed_ratio:.1f}x real-time\n")
        
        # Engine and model info
        lines.append(f"Engine:            {engine}\n")
        lines.append(f"Model:             {model}\n")
        lines.append(f"Compute Precision: {compute_type}\n")
        lines.append(f"Language:          {language}\n")
        
        # Confidence score
        if avg_confidence is not None:
            confidence_pct = (1 + avg_confidence) * 100
            lines.append(f"Confidence:        {confidence_pct:.1f}%\n")
        
        lines.append("=" * 60 + "\n\n")
        
        return ''.join(lines)

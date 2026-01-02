"""Formatting utilities for Audio Transcriber."""
from config.constants import SECONDS_PER_MINUTE, SECONDS_PER_HOUR, BYTES_PER_KB, BYTES_PER_MB


class FormatUtils:
    """Utilities for text and time formatting."""
    
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

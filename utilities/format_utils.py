"""Formatting utilities for Audio Transcriber."""


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
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}h {minutes}m {secs:.0f}s"
    
    @staticmethod
    def format_text_with_line_breaks(text, max_chars=80):
        """Format text with line breaks based on character length, without breaking words.
        
        Args:
            text: The text to format.
            max_chars: Maximum characters per line (0 = no breaks).
        
        Returns:
            Formatted text with line breaks.
        """
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
        size_mb = size_bytes / (1024 * 1024)
        if size_mb < 1:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_mb < 1024:
            return f"{size_mb:.1f} MB"
        else:
            return f"{size_mb / 1024:.1f} GB"

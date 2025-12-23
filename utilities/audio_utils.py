"""Audio utilities for Audio Transcriber."""


class AudioUtils:
    """Utilities for audio metadata formatting."""
    
    @staticmethod
    def format_audio_info(metadata):
        """Format audio metadata for display.
        
        Args:
            metadata: Dictionary of audio metadata.
            
        Returns:
            Formatted audio info string.
        """
        info = []
        
        # Audio format details
        if metadata.get('channels'):
            if metadata['channels'] == 1:
                info.append("Mono")
            elif metadata['channels'] == 2:
                info.append("Stereo")
            else:
                info.append(f"{metadata['channels']} channels")
        
        if metadata.get('sample_rate'):
            sample_rate = metadata['sample_rate']
            if sample_rate >= 1000:
                info.append(f"{sample_rate / 1000:.1f}kHz")
            else:
                info.append(f"{sample_rate}Hz")
        
        if metadata.get('bitrate'):
            info.append(f"{metadata['bitrate']}kbps")
        
        return " / ".join(info) if info else "Unknown"
    
    @staticmethod
    def format_mp3_tags(metadata):
        """Format MP3 ID3 tag information for display.
        
        Args:
            metadata: Dictionary of audio metadata.
            
        Returns:
            Formatted MP3 tags string or None.
        """
        tags = []
        
        if metadata.get('artist'):
            tags.append(f"Artist: {metadata['artist']}")
        
        if metadata.get('album'):
            tags.append(f"Album: {metadata['album']}")
        
        if metadata.get('title'):
            tags.append(f"Title: {metadata['title']}")
        
        return "\n".join(tags) if tags else None

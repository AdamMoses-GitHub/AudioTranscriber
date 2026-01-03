"""Metadata extractor for audio files."""
import os
from config.environment import PYDUB_AVAILABLE, WAVE_AVAILABLE, MUTAGEN_AVAILABLE

if PYDUB_AVAILABLE:
    from pydub import AudioSegment

if WAVE_AVAILABLE:
    import wave

if MUTAGEN_AVAILABLE:
    from mutagen.id3 import ID3


class MetadataExtractor:
    """Extracts metadata from audio files."""
    
    @staticmethod
    def get_audio_metadata(audio_file):
        """Extract audio file metadata (bitrate, channels, sample rate, ID3 tags, etc.).
        
        Args:
            audio_file: Path to audio file.
            
        Returns:
            Dictionary of metadata.
        """
        metadata = {
            'bitrate': None,
            'channels': None,
            'sample_rate': None,
            'codec': None,
            'title': None,
            'artist': None,
            'album': None
        }
        
        try:
            file_ext = os.path.splitext(audio_file)[1].lower()
            
            # Extract ID3 tags for MP3 files
            if file_ext == '.mp3' and MUTAGEN_AVAILABLE:
                try:
                    audio = ID3(audio_file)
                    if 'TIT2' in audio:  # Title
                        metadata['title'] = str(audio['TIT2'])
                    if 'TPE1' in audio:  # Artist
                        metadata['artist'] = str(audio['TPE1'])
                    if 'TALB' in audio:  # Album
                        metadata['album'] = str(audio['TALB'])
                except Exception as e:
                    import logging
                    logging.debug(f"Error extracting ID3 tags: {e}")
            
            # Try pydub for common formats
            if PYDUB_AVAILABLE:
                try:
                    audio = AudioSegment.from_file(audio_file)
                    metadata['channels'] = audio.channels
                    metadata['sample_rate'] = audio.frame_rate
                    metadata['bitrate'] = audio.frame_rate * audio.frame_width * 8 * audio.channels // 1000
                except Exception as e:
                    import logging
                    logging.debug(f"Error extracting metadata with pydub: {e}")
            
            # Fallback for WAV files
            if file_ext == '.wav' and WAVE_AVAILABLE:
                try:
                    with wave.open(audio_file, 'rb') as wav:
                        metadata['channels'] = wav.getnchannels()
                        metadata['sample_rate'] = wav.getframerate()
                except Exception as e:
                    import logging
                    logging.debug(f"Error extracting WAV metadata: {e}")
                    
        except Exception as e:
            import logging
            logging.debug(f"Error extracting audio metadata from {audio_file}: {e}")
            
        return metadata

"""Metadata extractor for audio files."""
import os
from config.environment import PYDUB_AVAILABLE, WAVE_AVAILABLE, MUTAGEN_AVAILABLE
from config.logger import get_logger

logger = get_logger(__name__)

if PYDUB_AVAILABLE:
    from pydub import AudioSegment

if WAVE_AVAILABLE:
    import wave

if MUTAGEN_AVAILABLE:
    from mutagen.id3 import ID3
    try:
        from mutagen import File as MutagenFile
    except Exception:
        MutagenFile = None
else:
    MutagenFile = None


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
            'duration_seconds': None,
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
                    logger.debug(f"Error extracting ID3 tags: {e}")

            # Fast path: use mutagen headers (no full audio decode) when available.
            if MUTAGEN_AVAILABLE and MutagenFile is not None:
                try:
                    audio_obj = MutagenFile(audio_file)
                    info = getattr(audio_obj, 'info', None) if audio_obj is not None else None
                    if info is not None:
                        channels = getattr(info, 'channels', None)
                        sample_rate = getattr(info, 'sample_rate', None)
                        length_seconds = getattr(info, 'length', None)
                        bitrate_bps = getattr(info, 'bitrate', None)

                        if channels is not None:
                            metadata['channels'] = channels
                        if sample_rate is not None:
                            metadata['sample_rate'] = sample_rate
                        if length_seconds is not None:
                            metadata['duration_seconds'] = float(length_seconds)
                        if bitrate_bps is not None:
                            metadata['bitrate'] = int(bitrate_bps / 1000)
                        metadata['codec'] = type(audio_obj).__name__
                except Exception as e:
                    logger.debug(f"Error extracting metadata with mutagen: {e}")

            # Fast WAV header fallback for duration/rate/channels.
            if file_ext == '.wav' and WAVE_AVAILABLE:
                needs_wav_probe = any(
                    metadata.get(key) is None for key in ('channels', 'sample_rate', 'duration_seconds')
                )
                if needs_wav_probe:
                    try:
                        with wave.open(audio_file, 'rb') as wav:
                            metadata['channels'] = wav.getnchannels()
                            metadata['sample_rate'] = wav.getframerate()
                            frame_rate = wav.getframerate()
                            total_frames = wav.getnframes()
                            if frame_rate and frame_rate > 0:
                                metadata['duration_seconds'] = total_frames / frame_rate
                    except Exception as e:
                        logger.debug(f"Error extracting WAV metadata: {e}")
            
            # Use pydub only as a fallback when key metadata is still missing.
            needs_decode = any(
                metadata.get(key) is None for key in ('channels', 'sample_rate', 'bitrate', 'duration_seconds')
            )
            if needs_decode and PYDUB_AVAILABLE:
                try:
                    audio = AudioSegment.from_file(audio_file)
                    metadata['channels'] = audio.channels
                    metadata['sample_rate'] = audio.frame_rate
                    metadata['bitrate'] = audio.frame_rate * audio.frame_width * 8 * audio.channels // 1000
                    metadata['duration_seconds'] = len(audio) / 1000.0
                except Exception as e:
                    logger.debug(f"Error extracting metadata with pydub: {e}")
                    
        except Exception as e:
            logger.debug(f"Error extracting audio metadata from {audio_file}: {e}")
            
        return metadata

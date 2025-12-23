"""File utilities for Audio Transcriber."""
import os
from config.constants import AUDIO_EXTENSIONS


class FileUtils:
    """Utilities for file operations."""
    
    @staticmethod
    def get_audio_files(folder, recursive=False):
        """Get list of audio files in a folder.
        
        Args:
            folder: Folder path to search.
            recursive: Whether to search recursively.
            
        Returns:
            Sorted list of audio file paths.
        """
        audio_files = []
        
        if recursive:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if os.path.splitext(file)[1].lower() in AUDIO_EXTENSIONS:
                        audio_files.append(os.path.join(root, file))
        else:
            try:
                for file in os.listdir(folder):
                    file_path = os.path.join(folder, file)
                    if os.path.isfile(file_path) and os.path.splitext(file)[1].lower() in AUDIO_EXTENSIONS:
                        audio_files.append(file_path)
            except Exception:
                pass
        
        return sorted(audio_files)
    
    @staticmethod
    def get_relative_path(file_path, base_folder):
        """Get relative path from base folder.
        
        Args:
            file_path: Full file path.
            base_folder: Base folder path.
            
        Returns:
            Relative path from base folder.
        """
        try:
            return os.path.relpath(file_path, base_folder)
        except ValueError:
            return os.path.basename(file_path)
    
    @staticmethod
    def ensure_directory(file_path):
        """Ensure directory exists for a file path.
        
        Args:
            file_path: File path to ensure directory for.
        """
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

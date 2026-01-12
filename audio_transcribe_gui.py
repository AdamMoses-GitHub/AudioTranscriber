"""Audio Transcriber - Main entry point.

A comprehensive audio transcription application using OpenAI Whisper and Faster-Whisper.
Supports single file and batch processing with GPU acceleration.
"""
import sys
import logging
import tkinter as tk
from tkinter import messagebox
from ui import AudioTranscriberApp


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audio_transcriber.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application."""
    try:
        logger.info("Starting Audio Transcriber application")
        root = tk.Tk()
        app = AudioTranscriberApp(root)
        root.mainloop()
        logger.info("Application closed normally")
    except ImportError as e:
        logger.error(f"Import error: {e}", exc_info=True)
        messagebox.showerror(
            "Import Error",
            f"Failed to import required modules: {e}\n\nPlease ensure all dependencies are installed."
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        messagebox.showerror(
            "Application Error",
            f"An unexpected error occurred: {e}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

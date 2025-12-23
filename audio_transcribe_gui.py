"""Audio Transcriber - Main entry point.

A comprehensive audio transcription application using OpenAI Whisper and Faster-Whisper.
Supports single file and batch processing with GPU acceleration.
"""
import tkinter as tk
from ui import AudioTranscriberApp


def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = AudioTranscriberApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

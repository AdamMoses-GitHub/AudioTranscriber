"""Audio Transcriber - Main entry point.

A comprehensive audio transcription application using OpenAI Whisper and Faster-Whisper.
Supports single file and batch processing with GPU acceleration.
"""
import sys
import tkinter as tk
from tkinter import messagebox
from ui import AudioTranscriberApp


def main():
    """Main entry point for the application."""
    try:
        root = tk.Tk()
        app = AudioTranscriberApp(root)
        root.mainloop()
    except ImportError as e:
        messagebox.showerror(
            "Import Error",
            f"Failed to import required modules: {e}\n\nPlease ensure all dependencies are installed."
        )
        sys.exit(1)
    except Exception as e:
        messagebox.showerror(
            "Application Error",
            f"An unexpected error occurred: {e}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Audio Transcriber - Main entry point.

A comprehensive audio transcription application using OpenAI Whisper and Faster-Whisper.
Supports single file and batch processing with GPU acceleration.
"""
import faulthandler
import os
import sys
import logging
import threading
import tkinter as tk
from tkinter import messagebox


# Disable progress-bar monitor threads that can cause instability in long GUI runs.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")


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


def _install_crash_logging():
    """Capture uncaught exceptions and fatal faults in the log file."""
    log_path = os.path.abspath('audio_transcriber.log')
    crash_log = open(log_path, 'a', buffering=1, encoding='utf-8')

    faulthandler.enable(file=crash_log, all_threads=True)

    def handle_uncaught_exception(exc_type, exc_value, exc_tb):
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    def handle_thread_exception(args):
        logger.error(
            "Uncaught thread exception in %s",
            args.thread.name if args.thread else 'unknown',
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = handle_uncaught_exception
    threading.excepthook = handle_thread_exception

    logger.info("Crash logging enabled: %s", log_path)
    logger.info("Process info: pid=%s python=%s cwd=%s", os.getpid(), sys.executable, os.getcwd())
    return crash_log


def main():
    """Main entry point for the application."""
    crash_log = None
    try:
        from ui import AudioTranscriberApp
        crash_log = _install_crash_logging()
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
    finally:
        if crash_log is not None:
            try:
                crash_log.flush()
                crash_log.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()

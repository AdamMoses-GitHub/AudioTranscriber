"""About tab showing program information."""
import tkinter as tk
from tkinter import ttk


class AboutTab:
    """About tab UI."""
    
    def __init__(self, parent_notebook, app_controller):
        """Initialize about tab.
        
        Args:
            parent_notebook: Parent notebook widget.
            app_controller: Main application controller with shared resources.
        """
        self.parent = parent_notebook
        self.app = app_controller
        
        # Create tab frame
        self.frame = ttk.Frame(parent_notebook, padding="20")
        parent_notebook.add(self.frame, text="About")
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self):
        """Create UI components."""
        self.frame.columnconfigure(0, weight=1)
        
        # Title
        title = ttk.Label(self.frame, text="Audio Transcriber", 
                         font=("Arial", 18, "bold"))
        title.grid(row=0, column=0, pady=(20, 10))
        
        # Version
        version = ttk.Label(self.frame, text="Version 1.0", 
                           font=("Arial", 10, "italic"),
                           foreground="gray")
        version.grid(row=1, column=0, pady=(0, 30))
        
        # Personal intro
        intro_frame = ttk.LabelFrame(self.frame, text="About This Project", padding="10")
        intro_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        intro_frame.columnconfigure(0, weight=1)
        
        intro_text = (
            "I'm Adam Moses, and I wanted to create a simple-to-use audio "
            "transcription program using open source tools. My goal was to make "
            "something that's fast and leverages GPU acceleration where possible, "
            "making it especially useful for podcasts and other long-form content. "
            "I intend to add more capabilities over time, continuously improving "
            "the tool based on real-world use cases.\n\n"
            "Project Repository:\n"
            "https://github.com/AdamMoses-GitHub/AudioTranscriber"
        )
        
        intro_label = tk.Text(intro_frame, wrap=tk.WORD, font=("Arial", 10),
                             height=6, relief=tk.FLAT, borderwidth=0,
                             highlightthickness=0)
        intro_label.insert("1.0", intro_text)
        intro_label.config(state="disabled")
        intro_label.grid(row=0, column=0, sticky="ew")
        
        # Description
        desc_frame = ttk.Frame(self.frame)
        desc_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        desc_frame.columnconfigure(0, weight=1)
        
        description = (
            "Audio Transcriber is a powerful desktop application for converting "
            "audio files into text using OpenAI's Whisper speech recognition models.\n\n"
            "Key Features:\n\n"
            "• Single File Transcription - Process individual audio files with "
            "detailed metadata and customizable formatting options\n\n"
            "• Batch Processing - Transcribe multiple files at once with progress "
            "tracking, summary reports, and folder structure preservation\n\n"
            "• GPU Acceleration - Leverage NVIDIA CUDA-enabled GPUs for faster "
            "processing (up to 10x real-time speed)\n\n"
            "• Flexible Configuration - Choose from multiple Whisper model sizes "
            "(tiny to large-v3) balancing speed, accuracy, and resource usage\n\n"
            "• Audio Format Support - Compatible with MP3, WAV, M4A, FLAC, AAC, "
            "OGG, and WebM formats\n\n"
            "• Metadata Extraction - Automatically detects recording dates from "
            "filenames and extracts MP3 ID3 tags\n\n"
            "• Text Formatting - Optional line breaks and wrapping for improved "
            "readability\n\n"
            "The application uses state-of-the-art AI models to deliver highly "
            "accurate transcriptions with confidence scoring and automatic language "
            "detection. Perfect for transcribing meetings, interviews, lectures, "
            "podcasts, and any other audio content."
        )
        
        desc_label = tk.Text(desc_frame, wrap=tk.WORD, font=("Arial", 10),
                            height=25, relief=tk.FLAT, borderwidth=0,
                            highlightthickness=0)
        desc_label.insert("1.0", description)
        desc_label.config(state="disabled")
        desc_label.grid(row=0, column=0, sticky="ew")
        
        # System info
        info_frame = ttk.LabelFrame(self.frame, text="System Information", padding="10")
        info_frame.grid(row=4, column=0, sticky="ew", pady=(20, 0))
        
        gpu_status = self.app.environment.get_gpu_status_text()
        
        info_text = f"GPU Available: {gpu_status}\n"
        if self.app.environment.gpu_available:
            gpu_info = self.app.environment.get_gpu_info()
            info_text += f"GPU Device: {gpu_info['name']}\n"
        
        info_label = ttk.Label(info_frame, text=info_text, font=("Arial", 9))
        info_label.grid(row=0, column=0, sticky="w")

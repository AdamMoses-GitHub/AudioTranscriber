"""Single file transcription tab."""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import time
import threading
from utilities.format_utils import FormatUtils
from utilities.date_parser import DateParser
from utilities.audio_utils import AudioUtils
from config.constants import TIMESTAMP_FORMATS, TIMESTAMP_INTERVALS, DEFAULT_TIMESTAMP_FORMAT, DEFAULT_TIMESTAMP_INTERVAL


class SingleFileTab:
    """Single file transcription tab UI."""
    
    def __init__(self, parent_notebook, app_controller):
        """Initialize single file tab.
        
        Args:
            parent_notebook: Parent notebook widget.
            app_controller: Main application controller with shared resources.
        """
        self.parent = parent_notebook
        self.app = app_controller
        
        # Create tab frame
        self.frame = ttk.Frame(parent_notebook, padding="10")
        parent_notebook.add(self.frame, text="Single File")
        
        # State variables
        self.file_path = None
        self.processing = False
        self.cancel_requested = False
        self.current_transcript = None
        
        # Configuration variables
        self.detect_date = tk.BooleanVar(value=True)
        self.chars_per_line = tk.IntVar(value=80)
        self.timestamps_enabled = tk.BooleanVar(value=False)
        self.timestamp_format = tk.StringVar(value=DEFAULT_TIMESTAMP_FORMAT)
        self.timestamp_interval = tk.IntVar(value=DEFAULT_TIMESTAMP_INTERVAL)
        
        # Create UI
        self._create_ui()
        
    def _create_ui(self):
        """Create UI components."""
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(4, weight=1)
        
        # Title
        title = ttk.Label(self.frame, text="Single File Transcription", 
                         font=("Arial", 14, "bold"))
        title.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # File selection
        file_frame = ttk.LabelFrame(self.frame, text="File Selection", padding="10")
        file_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="Audio File:").grid(row=0, column=0, sticky="w", pady=5)
        
        file_select_frame = ttk.Frame(file_frame)
        file_select_frame.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        file_select_frame.columnconfigure(0, weight=1)
        
        self.file_label = ttk.Label(file_select_frame, text="No file selected",
                                     foreground="gray", relief=tk.SUNKEN, anchor=tk.W,
                                     padding=(5, 2))
        self.file_label.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        ttk.Button(file_select_frame, text="Browse", 
                  command=self.select_file).grid(row=0, column=1)
        
        # Options
        options_frame = ttk.LabelFrame(self.frame, text="Options", padding="10")
        options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        # Date detection with help button
        date_frame = ttk.Frame(options_frame)
        date_frame.grid(row=0, column=0, sticky="w")
        
        ttk.Checkbutton(date_frame, text="Detect recording date from filename",
                       variable=self.detect_date,
                       command=self.app.save_config).grid(row=0, column=0, sticky="w")
        
        help_btn = ttk.Button(date_frame, text="?", width=3, command=self.show_date_detection_help)
        help_btn.grid(row=0, column=1, padx=(5, 0))
        
        # Format text option
        format_frame = ttk.Frame(options_frame)
        format_frame.grid(row=0, column=1, sticky="w", padx=(20, 0))
        
        ttk.Label(format_frame, text="Characters per line:").grid(row=0, column=0, sticky="w")
        words_spin = ttk.Spinbox(format_frame, from_=0, to=200, width=8, 
                                textvariable=self.chars_per_line,
                                command=self.app.save_config)
        words_spin.grid(row=0, column=1, padx=(5, 5))
        self.chars_per_line.trace_add('write', lambda *args: self.app.save_config())
        ttk.Label(format_frame, text="(0 = no breaks)", foreground="gray", 
                 font=("Arial", 8)).grid(row=0, column=2, sticky="w")
        ttk.Button(format_frame, text="?", width=3, command=self.show_chars_per_line_help).grid(
            row=0, column=3, padx=(5, 0))
        
        # Timestamp options
        timestamp_frame = ttk.Frame(options_frame)
        timestamp_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        
        self.timestamps_checkbox = ttk.Checkbutton(
            timestamp_frame, 
            text="Include timestamps",
            variable=self.timestamps_enabled,
            command=self._on_timestamp_toggle
        )
        self.timestamps_checkbox.grid(row=0, column=0, sticky="w")
        
        ttk.Label(timestamp_frame, text="Format:").grid(row=0, column=1, sticky="w", padx=(20, 5))
        self.format_combo = ttk.Combobox(
            timestamp_frame,
            textvariable=self.timestamp_format,
            values=TIMESTAMP_FORMATS,
            state="readonly",
            width=12
        )
        self.format_combo.grid(row=0, column=2, sticky="w")
        self.format_combo.bind('<<ComboboxSelected>>', lambda e: self.app.save_config())
        
        ttk.Label(timestamp_frame, text="Interval:").grid(row=0, column=3, sticky="w", padx=(20, 5))
        self.interval_combo = ttk.Combobox(
            timestamp_frame,
            textvariable=self.timestamp_interval,
            values=TIMESTAMP_INTERVALS,
            state="readonly",
            width=8
        )
        self.interval_combo.grid(row=0, column=4, sticky="w")
        self.interval_combo.bind('<<ComboboxSelected>>', lambda e: self.app.save_config())
        
        ttk.Label(timestamp_frame, text="seconds", foreground="gray", font=("Arial", 8)).grid(
            row=0, column=5, sticky="w", padx=(5, 0))
        
        ttk.Button(timestamp_frame, text="?", width=3, command=self.show_timestamp_help).grid(
            row=0, column=6, padx=(5, 0))
        
        # Initially disable timestamp controls, if widgets are available
        if hasattr(self, "format_combo") and hasattr(self, "interval_combo"):
            self._on_timestamp_toggle()
        
        # Control buttons
        control_frame = ttk.Frame(self.frame)
        control_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        
        self.transcribe_btn = ttk.Button(control_frame, text="Transcribe File",
                                         command=self.transcribe_file,
                                         state="disabled")
        self.transcribe_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.cancel_btn = ttk.Button(control_frame, text="Cancel",
                                     command=self.cancel_processing,
                                     state="disabled")
        self.cancel_btn.grid(row=0, column=1)
        
        # Progress
        self.progress = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # Results
        results_frame = ttk.LabelFrame(self.frame, text="Transcription Result", padding="10")
        results_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        self.text_area = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD,
                                                   font=("Consolas", 10))
        self.text_area.grid(row=0, column=0, sticky="nsew")
        
        # Save button below transcription area
        self.save_btn = ttk.Button(results_frame, text="Save Transcript To File",
                                   command=self.save_transcript,
                                   state="disabled")
        self.save_btn.grid(row=1, column=0, pady=(10, 0))
        
        # Status bar
        self.status = tk.StringVar(value="Ready - Select an audio file to begin")
        status_bar = ttk.Label(self.frame, textvariable=self.status,
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=5, column=0, sticky="ew", pady=(10, 0))
    
    def select_file(self):
        """Select audio file."""
        file_types = [
            ("Audio files", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.webm"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(title="Select Audio File", filetypes=file_types)
        
        if filename:
            self.file_path = filename
            self.file_label.config(text=filename, foreground="black")
            self.transcribe_btn.config(state="normal")
            
            file_size = os.path.getsize(filename) / (1024 * 1024)
            self.status.set(f"Selected: {os.path.basename(filename)} ({file_size:.1f} MB)")
            
            self.app.save_config()
    
    def transcribe_file(self):
        """Start transcription."""
        if not self.file_path:
            messagebox.showerror("Error", "Please select an audio file first.")
            return
        
        self.cancel_requested = False
        self.transcribe_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress.start()
        self.text_area.delete("1.0", tk.END)
        
        # Freeze other tabs
        self.app.freeze_other_tabs(0)
        
        threading.Thread(target=self._transcribe_worker, daemon=True).start()
    
    def _transcribe_worker(self):
        """Worker thread for transcription."""
        try:
            file_size = os.path.getsize(self.file_path) / (1024 * 1024)
            
            self.update_status("Loading model...")
            self.app.model_manager.load_model(
                self.app.engine.get(),
                self.app.model_size.get(),
                self.app.compute_type.get()
            )
            
            start_time = time.time()
            
            self.update_status("Transcribing audio...")
            
            # Build options dict with timestamp settings
            options = {
                'timestamps_enabled': self.timestamps_enabled.get(),
                'timestamp_format': self.timestamp_format.get(),
                'timestamp_interval': self.timestamp_interval.get()
            }
            
            result = self.app.transcriber.transcribe_with_metadata(
                self.file_path,
                self.app.engine.get(),
                options=options
            )
            
            # Extract results
            if isinstance(result, dict):
                text = result.get('text', '')
                language = result.get('language', 'Unknown')
                duration = result.get('duration', 0)
                avg_confidence = result.get('avg_logprob', None)
                audio_metadata = result.get('audio_metadata', {})
            else:
                text = result
                language = 'Unknown'
                duration = 0
                avg_confidence = None
                audio_metadata = {}
            
            processing_time = time.time() - start_time
            
            if self.cancel_requested:
                self.update_status("Transcription cancelled")
                return
            
            # Format text if requested
            if self.chars_per_line.get() > 0:
                text = FormatUtils.format_text_with_line_breaks(text, self.chars_per_line.get())
            
            # Detect date if requested
            date_info = ""
            if self.detect_date.get():
                detected_date, day_of_week = DateParser.detect_date_from_filename(
                    os.path.basename(self.file_path)
                )
                if detected_date:
                    date_info = f"Recording Date: {detected_date.strftime('%Y-%m-%d')} ({day_of_week})\n"
            
            # Prepare final text
            final_text = f"Transcript of: {os.path.basename(self.file_path)}\n"
            final_text += date_info
            final_text += f"Transcribed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            final_text += "\n--- TRANSCRIPTION METADATA ---\n"
            final_text += f"File Size:         {file_size:.2f} MB\n"
            
            audio_info = AudioUtils.format_audio_info(audio_metadata)
            if audio_info != "Unknown":
                final_text += f"Audio Format:      {audio_info}\n"
            
            mp3_tags = AudioUtils.format_mp3_tags(audio_metadata)
            if mp3_tags:
                final_text += f"MP3 Tags:\n{mp3_tags}\n"
            
            if duration > 0:
                final_text += f"Duration:          {FormatUtils.format_time(duration)}\n"
            final_text += f"Processing Time:   {FormatUtils.format_time(processing_time)}\n"
            if duration > 0:
                speed_ratio = duration / processing_time
                final_text += f"Speed:             {speed_ratio:.1f}x real-time\n"
            final_text += f"Engine:            {self.app.engine.get()}\n"
            final_text += f"Model:             {self.app.model_size.get()}\n"
            final_text += f"Compute Precision: {self.app.compute_type.get()}\n"
            if self.app.environment.gpu_available:
                gpu_name = self.app.environment.get_gpu_info()['name']
                final_text += f"GPU:               {gpu_name}\n"
            else:
                final_text += f"Device:            CPU\n"
            final_text += f"Language:          {language}\n"
            if avg_confidence is not None:
                confidence_pct = (1 + avg_confidence) * 100
                final_text += f"Confidence:        {confidence_pct:.1f}%\n"
            final_text += "=" * 60 + "\n\n"
            final_text += text
            
            # Store transcript and display in text area
            self.current_transcript = final_text
            self.app.root.after(0, lambda: self.text_area.insert("1.0", final_text))
            self.app.root.after(0, lambda: self.save_btn.config(state="normal"))
            
            self.update_status("Transcription complete - Use 'Save Transcript To File' to save")
            
        except Exception as e:
            self.app.root.after(0, lambda e=e: messagebox.showerror("Error", f"Transcription failed: {e}"))
            self.update_status("Transcription failed")
        finally:
            self.app.model_manager.cleanup_model()
            self.app.root.after(0, self.progress.stop)
            self.app.root.after(0, lambda: self.transcribe_btn.config(state="normal"))
            self.app.root.after(0, lambda: self.cancel_btn.config(state="disabled"))
            self.app.root.after(0, self.app.unfreeze_all_tabs)
    
    def cancel_processing(self):
        """Cancel processing."""
        self.cancel_requested = True
        self.cancel_btn.config(state="disabled")
    
    def save_transcript(self):
        """Save transcript to file."""
        if not self.current_transcript:
            messagebox.showwarning("No Transcript", "No transcript available to save.")
            return
        
        # Suggest filename based on source audio file
        default_name = "transcript.txt"
        if self.file_path:
            default_name = os.path.splitext(os.path.basename(self.file_path))[0] + '.txt'
        
        filename = filedialog.asksaveasfilename(
            title="Save Transcript As",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.current_transcript)
                self.status.set(f"Transcript saved to {os.path.basename(filename)}")
                messagebox.showinfo("Success", f"Transcript saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save transcript:\n{e}")
    
    def update_status(self, message):
        """Update status message."""
        self.app.root.after(0, lambda: self.status.set(message))
    
    def _on_timestamp_toggle(self):
        """Handle timestamp checkbox toggle."""
        state = "readonly" if self.timestamps_enabled.get() else "disabled"
        self.format_combo.config(state=state)
        self.interval_combo.config(state=state)
        self.app.save_config()
    
    def show_date_detection_help(self):
        """Show help dialog for date detection feature."""
        help_text = (
            "Date Detection from Filename\n\n"
            "This feature automatically extracts the recording date from the audio filename.\n\n"
            "Supported formats:\n"
            "  • YYYY-MM-DD  (e.g., 2024-03-15.mp3)\n"
            "  • YYYYMMDD    (e.g., 20240315.mp3)\n"
            "  • MM-DD-YYYY  (e.g., 03-15-2024.mp3)\n"
            "  • Month DD YYYY (e.g., March_15_2024.mp3)\n\n"
            "If a date is detected:\n"
            "  • The date and day of week are added to the transcript header\n"
            "  • Format: YYYY-MM-DD (DayOfWeek)\n\n"
            "If no date is found, the transcript is created without date information."
        )
        messagebox.showinfo("Date Detection Help", help_text, parent=self.frame)
    
    def show_chars_per_line_help(self):
        """Show help dialog for characters per line feature."""
        help_text = (
            "Characters Per Line\n\n"
            "Controls text formatting in the transcript by adding line breaks.\n\n"
            "How it works:\n"
            "  • Breaks long paragraphs into shorter lines\n"
            "  • Never breaks in the middle of a word\n"
            "  • Preserves natural paragraph breaks\n\n"
            "Settings:\n"
            "  • 80 characters (default): Good for most uses\n"
            "  • 0: No line breaks - keeps original formatting\n"
            "  • Higher values: Longer lines before wrapping\n\n"
            "Tip: Use 0 if you want continuous text without artificial breaks."
        )
        messagebox.showinfo("Characters Per Line Help", help_text, parent=self.frame)
    
    def show_timestamp_help(self):
        """Show help dialog for timestamp feature."""
        help_text = (
            "Timestamp Options\n\n"
            "Adds timestamps at regular intervals throughout the transcript.\n\n"
            "Format Options:\n"
            "  • HH:MM:SS - Standard format (e.g., [01:23:45])\n"
            "  • MM:SS - Minutes and seconds only (e.g., [83:45])\n"
            "  • timecode - Includes milliseconds (e.g., [01:23:45.678])\n\n"
            "Interval Options:\n"
            "  • 15, 30, 60, 120, 300, 600 seconds\n"
            "  • Timestamps appear at the start of their own line\n"
            "  • First timestamp is always at 00:00:00\n\n"
            "Use timestamps to:\n"
            "  • Navigate long transcripts easily\n"
            "  • Reference specific parts of the audio\n"
            "  • Create timestamped notes\n\n"
            "Note: Timestamps are disabled by default."
        )
        messagebox.showinfo("Timestamp Help", help_text, parent=self.frame)
    
    def get_config(self):
        """Get tab configuration."""
        return {
            'file_path': self.file_path,
            'detect_date': self.detect_date.get(),
            'chars_per_line': self.chars_per_line.get(),
            'timestamps_enabled': self.timestamps_enabled.get(),
            'timestamp_format': self.timestamp_format.get(),
            'timestamp_interval': self.timestamp_interval.get()
        }
    
    def set_config(self, config):
        """Set tab configuration."""
        if config.get('file_path'):
            self.file_path = config['file_path']
            if os.path.exists(self.file_path):
                self.file_label.config(text=self.file_path, foreground="black")
                self.transcribe_btn.config(state="normal")
        
        if 'detect_date' in config:
            self.detect_date.set(config['detect_date'])
        
        if 'chars_per_line' in config:
            self.chars_per_line.set(config['chars_per_line'])
        
        if 'timestamps_enabled' in config:
            self.timestamps_enabled.set(config['timestamps_enabled'])
        
        if 'timestamp_format' in config:
            self.timestamp_format.set(config['timestamp_format'])
        
        if 'timestamp_interval' in config:
            self.timestamp_interval.set(config['timestamp_interval'])
        
        # Update timestamp control states
        self._on_timestamp_toggle()

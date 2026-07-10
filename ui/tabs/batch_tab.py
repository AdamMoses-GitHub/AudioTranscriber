"""Batch processing tab - PART 1 OF 2 - See continuation comment at end"""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import time
import threading
from datetime import datetime
from utilities.file_utils import FileUtils
from utilities.format_utils import FormatUtils
from config.constants import TIMESTAMP_FORMATS, TIMESTAMP_INTERVALS, DEFAULT_TIMESTAMP_FORMAT, DEFAULT_TIMESTAMP_INTERVAL


class BatchTab:
    """Batch processing tab UI."""
    
    def __init__(self, parent_notebook, app_controller):
        """Initialize batch tab."""
        self.parent = parent_notebook
        self.app = app_controller
        
        self.frame = ttk.Frame(parent_notebook, padding="10")
        parent_notebook.add(self.frame, text="Batch Processing")
        
        # State variables
        self.input_folder = None
        self.output_folder = None
        self.open_input_btn = None
        self.open_output_btn = None
        
        # Configuration variables
        self.detect_date = tk.BooleanVar(value=True)
        self.chars_per_line = tk.IntVar(value=80)
        self.skip_existing = tk.BooleanVar(value=True)
        self.create_summary = tk.BooleanVar(value=True)
        self.preserve_structure = tk.BooleanVar(value=False)
        self.recursive = tk.BooleanVar(value=False)
        self.timestamps_enabled = tk.BooleanVar(value=False)
        self.timestamp_format = tk.StringVar(value=DEFAULT_TIMESTAMP_FORMAT)
        self.timestamp_interval = tk.IntVar(value=DEFAULT_TIMESTAMP_INTERVAL)
        self.create_timestamped_log = tk.BooleanVar(value=False)
        self.crash_telemetry_enabled = tk.BooleanVar(value=False)
        self.crash_telemetry_every_files = tk.IntVar(value=25)
        
        # Diarization variables
        self.diarization_enabled = tk.BooleanVar(value=False)
        self.num_speakers = tk.IntVar(value=0)  # 0 = auto-detect
        self.diarization_timestamp_mode = tk.StringVar(value='speaker_turns')

        # Live metrics labels
        self.metrics_current_file_label = None
        self.metrics_total_progress_label = None
        self.metrics_meta_label = None
        self._metrics_refresh_job = None
        self._metrics_refresh_interval_ms = 500
        self.batch_state = "Idle"
        self.current_file_name = None
        self._metrics_samples_seen = 0
        self._metrics_time_sum = 0.0
        self._metrics_time_sq_sum = 0.0
        self._batch_log_file_path = None
        self._batch_log_file_handle = None
        self._batch_log_lock = threading.Lock()
        
        self._create_ui()
    
    def _create_ui(self):
        """Create UI components."""
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(4, weight=1)
        
        # Title
        ttk.Label(self.frame, text="Batch File Transcription",
                 font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Folder selection
        folder_frame = ttk.LabelFrame(self.frame, text="Folder Selection", padding="10")
        folder_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        folder_frame.columnconfigure(1, weight=1)
        
        # Input folder
        ttk.Label(folder_frame, text="Input Folder:").grid(row=0, column=0, sticky="w", pady=5)
        input_frame = ttk.Frame(folder_frame)
        input_frame.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=5)
        input_frame.columnconfigure(0, weight=1)
        
        self.input_label = ttk.Label(input_frame, text="No folder selected",
                                     foreground="gray", relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        self.input_label.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(input_frame, text="Browse", command=self.select_input).grid(row=0, column=1)
        self.open_input_btn = ttk.Button(
            input_frame,
            text="Open",
            command=lambda: self.open_folder_in_file_browser(self.input_folder),
            state="disabled"
        )
        self.open_input_btn.grid(row=0, column=2, padx=(5, 0))
        
        # Output folder
        ttk.Label(folder_frame, text="Output Folder:").grid(row=1, column=0, sticky="w", pady=5)
        output_frame = ttk.Frame(folder_frame)
        output_frame.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5)
        output_frame.columnconfigure(0, weight=1)
        
        self.output_label = ttk.Label(output_frame, text="No folder selected",
                                      foreground="gray", relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        self.output_label.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(output_frame, text="Browse", command=self.select_output).grid(row=0, column=1)
        self.open_output_btn = ttk.Button(
            output_frame,
            text="Open",
            command=lambda: self.open_folder_in_file_browser(self.output_folder),
            state="disabled"
        )
        self.open_output_btn.grid(row=0, column=2, padx=(5, 0))
        
        # Options
        options_frame = ttk.LabelFrame(self.frame, text="Processing Options", padding="10")
        options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        opts_grid = ttk.Frame(options_frame)
        opts_grid.grid(row=0, column=0, sticky="ew")
        
        # Date detection with help button
        date_frame = ttk.Frame(opts_grid)
        date_frame.grid(row=0, column=0, sticky="w", padx=(0, 15))
        
        ttk.Checkbutton(date_frame, text="Detect recording date from filename",
                       variable=self.detect_date, command=self.app.save_config).grid(
                           row=0, column=0, sticky="w")
        
        help_btn = ttk.Button(date_frame, text="?", width=3, command=self.show_date_detection_help)
        help_btn.grid(row=0, column=1, padx=(5, 0))
        
        format_frame = ttk.Frame(opts_grid)
        format_frame.grid(row=0, column=1, sticky="w", padx=(0, 15))
        ttk.Label(format_frame, text="Characters per line:").grid(row=0, column=0, sticky="w")
        words_spin = ttk.Spinbox(format_frame, from_=0, to=200, width=8,
                                textvariable=self.chars_per_line, command=self.app.save_config)
        words_spin.grid(row=0, column=1, padx=(5, 5))
        self.chars_per_line.trace_add('write', lambda *args: self.app.save_config())
        ttk.Label(format_frame, text="(0 = no breaks)", foreground="gray",
                 font=("Arial", 8)).grid(row=0, column=2, sticky="w")
        help_btn2 = ttk.Button(format_frame, text="?", width=3, command=self.show_chars_per_line_help)
        help_btn2.grid(row=0, column=3, padx=(5, 0))
        
        # Skip existing with help button
        skip_frame = ttk.Frame(opts_grid)
        skip_frame.grid(row=1, column=0, sticky="w", padx=(0, 15), pady=(5, 0))
        ttk.Checkbutton(skip_frame, text="Skip existing transcripts",
                       variable=self.skip_existing, command=self.app.save_config).grid(
                           row=0, column=0, sticky="w")
        ttk.Button(skip_frame, text="?", width=3, command=self.show_skip_existing_help).grid(
            row=0, column=1, padx=(5, 0))
        
        # Create summary with help button
        summary_frame = ttk.Frame(opts_grid)
        summary_frame.grid(row=1, column=1, sticky="w", padx=(0, 15), pady=(5, 0))
        ttk.Checkbutton(summary_frame, text="Create summary report",
                       variable=self.create_summary, command=self.app.save_config).grid(
                           row=0, column=0, sticky="w")
        ttk.Button(summary_frame, text="?", width=3, command=self.show_summary_help).grid(
            row=0, column=1, padx=(5, 0))
        
        # Preserve structure with help button
        preserve_frame = ttk.Frame(opts_grid)
        preserve_frame.grid(row=2, column=0, sticky="w", padx=(0, 15), pady=(5, 0))
        ttk.Checkbutton(preserve_frame, text="Preserve folder structure",
                       variable=self.preserve_structure, command=self.app.save_config).grid(
                           row=0, column=0, sticky="w")
        ttk.Button(preserve_frame, text="?", width=3, command=self.show_preserve_structure_help).grid(
            row=0, column=1, padx=(5, 0))
        
        # Recursive with help button
        recursive_frame = ttk.Frame(opts_grid)
        recursive_frame.grid(row=2, column=1, sticky="w", pady=(5, 0))
        ttk.Checkbutton(recursive_frame, text="Recursively check for audio files",
                       variable=self.recursive, command=self._on_recursive_toggle).grid(
                           row=0, column=0, sticky="w")
        ttk.Button(recursive_frame, text="?", width=3, command=self.show_recursive_help).grid(
            row=0, column=1, padx=(5, 0))

        log_file_frame = ttk.Frame(opts_grid)
        log_file_frame.grid(row=3, column=0, sticky="w", padx=(0, 15), pady=(5, 0))
        ttk.Checkbutton(
            log_file_frame,
            text="Create timestamped batch log file",
            variable=self.create_timestamped_log,
            command=self.app.save_config
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(log_file_frame, text="?", width=3, command=self.show_batch_log_file_help).grid(
            row=0, column=1, padx=(5, 0)
        )

        telemetry_frame = ttk.Frame(opts_grid)
        telemetry_frame.grid(row=3, column=1, sticky="w", pady=(5, 0))
        ttk.Checkbutton(
            telemetry_frame,
            text="Enable crash telemetry snapshots",
            variable=self.crash_telemetry_enabled,
            command=self.app.save_config
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(telemetry_frame, text="every", foreground="gray", font=("Arial", 8)).grid(
            row=0, column=1, sticky="w", padx=(8, 4)
        )
        telemetry_spin = ttk.Spinbox(
            telemetry_frame,
            from_=1,
            to=500,
            width=6,
            textvariable=self.crash_telemetry_every_files,
            command=self.app.save_config
        )
        telemetry_spin.grid(row=0, column=2, sticky="w")
        self.crash_telemetry_every_files.trace_add('write', lambda *args: self.app.save_config())
        ttk.Label(telemetry_frame, text="files", foreground="gray", font=("Arial", 8)).grid(
            row=0, column=3, sticky="w", padx=(4, 0)
        )
        ttk.Button(telemetry_frame, text="?", width=3, command=self.show_crash_telemetry_help).grid(
            row=0, column=4, padx=(5, 0)
        )

        # Timestamp options
        timestamp_frame = ttk.Frame(opts_grid)
        timestamp_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))
        
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
        
        # Initially disable timestamp controls
        self._on_timestamp_toggle()
        
        # Speaker Diarization section (optional feature)
        if self.app.environment.pyannote_available:
            diarization_frame = ttk.LabelFrame(opts_grid, text="Speaker Diarization (Optional)", padding="5")
            diarization_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
            
            diar_controls = ttk.Frame(diarization_frame)
            diar_controls.grid(row=0, column=0, sticky="w")
            
            # Enable checkbox
            self.diarization_checkbox = ttk.Checkbutton(
                diar_controls,
                text="Identify speakers",
                variable=self.diarization_enabled,
                command=self._on_diarization_toggle
            )
            self.diarization_checkbox.grid(row=0, column=0, sticky="w")
            
            # Number of speakers
            ttk.Label(diar_controls, text="Number of speakers:").grid(row=0, column=1, sticky="w", padx=(20, 5))
            self.speakers_spinbox = ttk.Spinbox(
                diar_controls,
                from_=0,
                to=10,
                width=5,
                textvariable=self.num_speakers,
                command=self.app.save_config
            )
            self.speakers_spinbox.grid(row=0, column=2, sticky="w")
            self.num_speakers.trace_add('write', lambda *args: self.app.save_config())
            
            ttk.Label(diar_controls, text="(0 = auto-detect)", foreground="gray", font=("Arial", 8)).grid(
                row=0, column=3, sticky="w", padx=(5, 0))
            
            ttk.Button(diar_controls, text="?", width=3, command=self.show_diarization_help).grid(
                row=0, column=4, padx=(5, 0))

            ttk.Label(diar_controls, text="Diarization timestamp mode:").grid(
                row=1, column=0, sticky="w", pady=(8, 0)
            )
            self.diarization_timestamp_combo = ttk.Combobox(
                diar_controls,
                textvariable=self.diarization_timestamp_mode,
                values=['speaker_turns', 'interval'],
                state='readonly',
                width=18
            )
            self.diarization_timestamp_combo.grid(row=1, column=1, columnspan=2, sticky="w", padx=(20, 0), pady=(8, 0))
            self.diarization_timestamp_combo.bind('<<ComboboxSelected>>', lambda e: self.app.save_config())
            
            # HF Token warning if not set
            if not self.app.hf_token.get():
                warning_frame = ttk.Frame(diarization_frame)
                warning_frame.grid(row=1, column=0, sticky="w", pady=(5, 0))
                ttk.Label(
                    warning_frame,
                    text="\u26a0\ufe0f Hugging Face token required. Configure in Model Configuration tab.",
                    foreground="red",
                    font=("Arial", 8)
                ).grid(row=0, column=0, sticky="w")
            
            # Initially disable diarization controls
            self._on_diarization_toggle()
        else:
            # Show message if pyannote not available
            unavail_frame = ttk.LabelFrame(opts_grid, text="Speaker Diarization (Not Available)", padding="5")
            unavail_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
            ttk.Label(
                unavail_frame,
                text="\u26a0\ufe0f pyannote.audio not installed. Run: pip install pyannote.audio torchaudio",
                foreground="gray",
                font=("Arial", 8)
            ).grid(row=0, column=0, sticky="w")
        
        # Control section
        control_frame = ttk.LabelFrame(self.frame, text="Batch Control", padding="10")
        control_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        control_frame.columnconfigure(0, weight=1)
        
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.start_btn = ttk.Button(btn_frame, text="Start Batch Processing",
                                    command=self.start_batch, state="disabled")
        self.start_btn.grid(row=0, column=0, padx=(0, 10))
        self.cancel_btn = ttk.Button(btn_frame, text="Cancel",
                                     command=self.cancel_batch, state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=(0, 10))
        ttk.Button(btn_frame, text="Clear Log", command=self.clear_log).grid(row=0, column=2)
        
        # Progress
        progress_frame = ttk.Frame(control_frame)
        progress_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        ttk.Label(progress_frame, text="Overall Progress:").grid(row=0, column=0, sticky="w")
        self.overall_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.overall_progress.grid(row=1, column=0, sticky="ew", pady=(2, 5))
        
        ttk.Label(progress_frame, text="Current File:").grid(row=2, column=0, sticky="w")
        self.current_progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.current_progress.grid(row=3, column=0, sticky="ew", pady=(2, 5))
        
        # Info panel with live metrics
        metrics_frame = ttk.LabelFrame(control_frame, text="Info Panel", padding="8")
        metrics_frame.grid(row=2, column=0, sticky="ew")
        metrics_frame.columnconfigure(0, weight=1)

        self.metrics_current_file_label = ttk.Label(
            metrics_frame,
            text="Current: - | Step: idle | Elapsed: 0s | Audio: - | ETA: calibrating",
            font=("Consolas", 9, "bold"),
            anchor="w"
        )
        self.metrics_current_file_label.grid(row=0, column=0, sticky="ew")

        self.metrics_total_progress_label = ttk.Label(
            metrics_frame,
            text="Total: Elapsed 0s | Audio 0s/0s | Files 0/0 | ETA calibrating",
            font=("Consolas", 9),
            foreground="gray",
            anchor="w",
            justify="left"
        )
        self.metrics_total_progress_label.grid(row=1, column=0, sticky="ew", pady=(3, 0))

        self.metrics_meta_label = ttk.Label(
            metrics_frame,
            text="Meta: Speed - | Trend - | Queue 0/0 | Fail 0.0% | Avg WPM - | ETA confidence Low",
            font=("Consolas", 9),
            foreground="gray",
            anchor="w",
            justify="left"
        )
        self.metrics_meta_label.grid(row=2, column=0, sticky="ew", pady=(3, 0))
        
        # Log
        log_frame = ttk.LabelFrame(self.frame, text="Processing Log", padding="10")
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        # Status bar
        self.status = tk.StringVar(value="Ready - Select input and output folders")
        ttk.Label(self.frame, textvariable=self.status,
                 relief=tk.SUNKEN, anchor=tk.W).grid(row=5, column=0, sticky="ew", pady=(10, 0))
    
    def select_input(self):
        """Select input folder."""
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            self.input_folder = folder
            self.input_label.config(text=folder, foreground="black")
            audio_files = FileUtils.get_audio_files(folder, self.recursive.get())
            self.log(f"📁 Input folder selected: {folder}")
            self.log(f"📊 Found {len(audio_files)} audio file(s)")
            self.check_ready()
            self._update_folder_open_buttons()
            self.app.save_config()
    
    def select_output(self):
        """Select output folder."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_label.config(text=folder, foreground="black")
            self.log(f"📁 Output folder selected: {folder}")
            self.check_ready()
            self._update_folder_open_buttons()
            self.app.save_config()

    def open_folder_in_file_browser(self, folder_path):
        """Open folder in the OS file browser if it exists."""
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showwarning("Folder Not Available", "The selected folder does not exist.", parent=self.frame)
            self._update_folder_open_buttons()
            return

        try:
            os.startfile(folder_path)
        except Exception as e:
            messagebox.showerror("Open Folder Error", f"Could not open folder:\n\n{e}", parent=self.frame)

    def _update_folder_open_buttons(self):
        """Enable/disable Open buttons based on selected folder existence."""
        if self.open_input_btn:
            input_exists = bool(self.input_folder and os.path.isdir(self.input_folder))
            self.open_input_btn.config(state="normal" if input_exists else "disabled")

        if self.open_output_btn:
            output_exists = bool(self.output_folder and os.path.isdir(self.output_folder))
            self.open_output_btn.config(state="normal" if output_exists else "disabled")
    
    def _on_recursive_toggle(self):
        """Handle recursive checkbox toggle — re-scan input folder and update button state."""
        self.app.save_config()
        if self.input_folder:
            audio_files = FileUtils.get_audio_files(self.input_folder, self.recursive.get())
            self.log(f"🔄 Recursive search {'enabled' if self.recursive.get() else 'disabled'}: found {len(audio_files)} audio file(s)")
            self.check_ready()

    def check_ready(self):
        """Check if batch processing is ready."""
        self._update_folder_open_buttons()
        if self.input_folder and self.output_folder:
            audio_files = FileUtils.get_audio_files(self.input_folder, self.recursive.get())
            if len(audio_files) > 0:
                self.start_btn.config(state="normal")
                self.status.set(f"Ready - {len(audio_files)} file(s) to process")
            else:
                self.start_btn.config(state="disabled")
                self.status.set("No audio files found")
        else:
            self.start_btn.config(state="disabled")
    
    def start_batch(self):
        """Start batch processing."""
        self._close_batch_log_file()
        audio_files = FileUtils.get_audio_files(self.input_folder, self.recursive.get())
        
        if not messagebox.askyesno("Start Batch Processing",
                                   f"Process {len(audio_files)} file(s)?\n\n"
                                   f"Engine: {self.app.engine.get()}\n"
                                   f"Model: {self.app.model_size.get()}"):
            return
        
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.overall_progress['maximum'] = len(audio_files)
        self.overall_progress['value'] = 0
        self.current_progress.start()
        
        self.app.freeze_other_tabs(1)
        
        self.log("=" * 80)
        self.log("🚀 Starting batch transcription...")
        self.log(f"📊 Total files: {len(audio_files)}")
        self.log("=" * 80)

        if self.create_timestamped_log.get():
            try:
                self._open_batch_log_file()
            except Exception as e:
                self.log(f"⚠️ Could not create batch log file: {e}")
        
        self._reset_metrics_panel()
        self.batch_state = "Starting"
        self._refresh_metrics_panel(current=0, total=len(audio_files), current_file=None)
        threading.Thread(target=self._batch_worker, daemon=True).start()
    
    def _batch_worker(self):
        """Batch processing worker thread."""
        diarizer_loaded = False
        try:
            effective_process_isolation = False

            # Load model
            success, error = self.app.model_manager.load_model(
                self.app.engine.get(),
                self.app.model_size.get(),
                self.app.compute_type.get()
            )
            if not success:
                self.log(f"Error: Failed to load model. {error}")
                self.app.root.after(0, lambda e=error: messagebox.showerror(
                    "Model Loading Error",
                    f"Failed to load model.\n\n{e}",
                    parent=self.frame
                ))
                return
            
            # Setup batch processor
            options = {
                'detect_date': self.detect_date.get(),
                'chars_per_line': self.chars_per_line.get(),
                'skip_existing': self.skip_existing.get(),
                'preserve_structure': self.preserve_structure.get(),
                'recursive': self.recursive.get(),
                'create_summary': self.create_summary.get(),
                'engine': self.app.engine.get(),
                'model': self.app.model_size.get(),
                'compute_type': self.app.compute_type.get(),
                'timestamps_enabled': self.timestamps_enabled.get(),
                'timestamp_format': self.timestamp_format.get(),
                'timestamp_interval': self.timestamp_interval.get(),
                'diarization_timestamp_mode': self.diarization_timestamp_mode.get(),
                'estimated_wpm': 150,
                'diarization_fallback_to_plain': True,
                # Duplicate-content hashing can be expensive on large batches.
                # Keep disabled by default for better stability.
                'skip_duplicates': False,
                'crash_telemetry_enabled': self.crash_telemetry_enabled.get(),
                'crash_telemetry_every_files': max(1, self.crash_telemetry_every_files.get()),
                'diarization_enabled': False  # Default
            }

            self.batch_state = "Pre-scan"
            # Pre-scan all files before actual processing to improve ETA and queue metrics.
            pre_scan_data = self.app.batch_processor.pre_scan_batch(
                self.input_folder,
                self.output_folder,
                options,
                log_callback=self.log
            )

            collision_count = len(pre_scan_data.get('output_path_collisions', []))
            if collision_count > 0:
                self.log("⚠️ Output collisions detected before run (same transcript path from multiple files)")
                for collision in pre_scan_data.get('output_path_collisions', [])[:3]:
                    sources = ", ".join(os.path.basename(p) for p in collision.get('audio_files', [])[:3])
                    self.log(f"   • {os.path.basename(collision.get('output_file', ''))}: {sources}")

            self.app.root.after(0, lambda: self._refresh_metrics_panel(current=0, total=pre_scan_data.get('total_files', 0), current_file=None))
            transcribe_total = pre_scan_data.get('estimated_total_files_to_transcribe', 0)
            progress_max = transcribe_total if transcribe_total > 0 else 1
            self.app.root.after(0, lambda m=progress_max: self.overall_progress.configure(maximum=m))
            
            # Check if diarization is enabled
            if self.diarization_enabled.get() and self.app.environment.pyannote_available:
                # Validate HF token
                hf_token = self.app.hf_token.get()
                if not hf_token or not hf_token.strip():
                    self.log("❌ Error: Hugging Face token required for diarization")
                    self.app.root.after(0, lambda: messagebox.showerror(
                        "Token Required",
                        "Please configure your Hugging Face token in the Model Configuration tab."))
                    return
                
                self.log("📍 Loading diarization model...")
                # Load diarization pipeline (will be reused for all files)
                success = self.app.diarizer.load_pipeline(hf_token, whisper_loaded=True)
                if not success:
                    self.log("❌ Failed to load diarization model")
                    self.app.root.after(0, lambda: messagebox.showerror(
                        "Diarization Error",
                        "Failed to load speaker diarization model. Check your token and connection."))
                    return
                
                diarizer_loaded = True
                self.log("✅ Diarization model loaded successfully")
                
                # Add diarization options
                options['diarization_enabled'] = True
                options['diarizer'] = self.app.diarizer
                options['num_speakers'] = self.num_speakers.get() if self.num_speakers.get() > 0 else None
            
            # Process batch
            results = self.app.batch_processor.process_batch(
                self.input_folder,
                self.output_folder,
                options,
                progress_callback=self._update_progress,
                log_callback=self.log,
                pre_scan_data=pre_scan_data
            )
            self.batch_state = "Done"
            
            self.log("\n" + "=" * 80)
            self.log("✅ Batch processing complete!")
            self.log(f"⏱️  Total time: {FormatUtils.format_time(results['total_time'])}")
            self.log(f"✅ Successful: {results['successful']}/{results['total']}")
            if results['failed'] > 0:
                self.log(f"❌ Failed: {results['failed']}")
            if results.get('skipped', 0) > 0:
                self.log(f"⏭️  Skipped existing: {results['skipped']}")
            self.log("=" * 80)

            self.app.root.after(0, lambda: self._refresh_metrics_panel(final=True))
            self.app.root.after(0, self.app.mark_batch_completed)
            
            if not self.app.batch_processor.cancel_requested:
                self.app.root.after(0, lambda: messagebox.showinfo(
                    "Batch Complete",
                    f"Successfully processed {results['successful']}/{results['total']} files"))
        
        except Exception as e:
            self.batch_state = "Error"
            self.log(f"\n❌ Error: {e}")
            self.app.root.after(0, lambda e=e: messagebox.showerror("Error", f"Batch failed: {e}"))
        finally:
            # Cleanup models
            self.app.model_manager.cleanup_model()
            if diarizer_loaded:
                self.app.diarizer.cleanup()
            
            # Safe memory trim after models are cleaned up
            try:
                import gc
                gc.collect()
                if self.app.environment.gpu_available:
                    import torch
                    torch.cuda.empty_cache()
            except Exception:
                pass
            
            self.app.root.after(0, self._reset_ui)
            self.app.root.after(0, self.app.unfreeze_all_tabs)
    
    def _update_progress(self, current, total, current_file):
        """Update progress."""
        file_name = os.path.basename(current_file) if current_file else "unknown"
        self._write_batch_log_file(f"PROGRESS {current}/{total}: {file_name}")
        stats = self.app.batch_processor.get_statistics(include_history=False)
        progress_value = stats.get('completed_transcribe_files', 0)
        self.app.root.after(0, lambda v=progress_value: self.overall_progress.configure(value=v))

        self.batch_state = "Running"
        self.current_file_name = os.path.basename(current_file) if current_file else None
        # Avoid queuing a full metrics refresh on every callback.
        # Periodic refresh handles UI updates at a bounded cadence.

    def _reset_metrics_panel(self):
        """Reset the info panel before a new run."""
        self._stop_metrics_refresh()
        self._metrics_samples_seen = 0
        self._metrics_time_sum = 0.0
        self._metrics_time_sq_sum = 0.0
        if self.metrics_current_file_label:
            self.metrics_current_file_label.config(text="Current: - | Step: idle | Elapsed: 0s | Audio: - | ETA: calibrating")
        if self.metrics_total_progress_label:
            self.metrics_total_progress_label.config(text="Total: Elapsed 0s | Audio 0s/0s | Files 0/0 | ETA calibrating")
        if self.metrics_meta_label:
            self.metrics_meta_label.config(text="Meta: Speed - | Trend - | Queue 0/0 | Fail 0.0% | Avg WPM - | ETA confidence Low")

    def _stop_metrics_refresh(self):
        """Stop scheduled live metrics updates."""
        if self._metrics_refresh_job is not None:
            try:
                self.app.root.after_cancel(self._metrics_refresh_job)
            except Exception:
                pass
            self._metrics_refresh_job = None

    def _schedule_metrics_refresh(self):
        """Schedule the next live metrics refresh while processing is active."""
        self._stop_metrics_refresh()
        if self.batch_state in {"Starting", "Pre-scan", "Running", "Canceling"}:
            self._metrics_refresh_job = self.app.root.after(self._metrics_refresh_interval_ms, self._refresh_metrics_panel)

    def _refresh_metrics_panel(self, current=None, total=None, current_file=None, final=False):
        """Refresh live metrics shown in the info panel."""
        stats = self.app.batch_processor.get_statistics(include_history=False)

        elapsed = stats.get('elapsed_seconds', 0)
        sample_count = stats.get('processing_sample_count', 0)
        processing_time_total = stats.get('processing_time_total', 0.0)
        avg_time = (processing_time_total / sample_count) if sample_count > 0 else 0

        total_transcribe_files = stats.get('estimated_total_files_to_transcribe', 0)
        completed_transcribe_files = stats.get('completed_transcribe_files', 0)
        completed_transcribe_audio = stats.get('completed_transcribe_audio_seconds', 0)
        total_transcribe_audio = stats.get('estimated_total_audio_seconds', 0)
        remaining_audio = max(0.0, total_transcribe_audio - completed_transcribe_audio)

        observed_speed_ratio = stats.get('observed_speed_ratio', 0)
        eta_ready = observed_speed_ratio > 0
        batch_eta_seconds = 0 if final else (remaining_audio / observed_speed_ratio if eta_ready and remaining_audio > 0 else 0)

        confidence = "Low"
        if sample_count >= 12:
            confidence = "High"
        elif sample_count >= 6:
            confidence = "Medium"

        current_file_stats = stats.get('current_file', {})
        current_name = current_file_stats.get('name') or self.current_file_name or "-"
        if len(current_name) > 52:
            current_name = "..." + current_name[-49:]
        current_step = current_file_stats.get('step') or self.batch_state.lower()
        current_elapsed = current_file_stats.get('elapsed_seconds', 0)
        current_audio_duration = current_file_stats.get('audio_duration_seconds', 0)
        current_eta_seconds = 0
        if eta_ready and current_audio_duration > 0 and current_step not in {'complete', 'failed', 'skipped', 'done'}:
            current_eta_seconds = max(0.0, (current_audio_duration / observed_speed_ratio) - current_elapsed)

        current_line = (
            f"Current: {current_name} | Step: {current_step} | "
            f"Elapsed: {FormatUtils.format_time(current_elapsed)} | "
            f"Audio: {FormatUtils.format_time(current_audio_duration)} | "
            f"ETA: {FormatUtils.format_time(current_eta_seconds) if eta_ready else 'calibrating'}"
        )

        total_line = (
            f"Total: Elapsed {FormatUtils.format_time(elapsed)} | "
            f"Audio {FormatUtils.format_time(completed_transcribe_audio)} / {FormatUtils.format_time(total_transcribe_audio)} | "
            f"Files {completed_transcribe_files}/{total_transcribe_files} | "
            f"ETA {FormatUtils.format_time(batch_eta_seconds) if eta_ready or final else 'calibrating'}"
        )

        processed_audio = stats.get('processed_audio_seconds', 0)
        avg_wpm = ((stats.get('total_words', 0) * 60.0) / processed_audio) if processed_audio > 0 else 0
        speed_text = f"{observed_speed_ratio:.2f}x" if eta_ready else "-"
        recent_speed_ratio = stats.get('recent_speed_ratio', 0)
        recent_speed_sample = stats.get('recent_speed_sample_size', 0)
        trend_text = "-"
        if eta_ready and recent_speed_sample > 0:
            delta = recent_speed_ratio - observed_speed_ratio
            if delta > 0.05:
                trend_state = "faster"
            elif delta < -0.05:
                trend_state = "slower"
            else:
                trend_state = "steady"
            trend_text = f"{recent_speed_ratio:.2f}x ({trend_state})"

        active_steps = {'queued', 'preparing', 'transcribing', 'formatting', 'writing'}
        queue_position = completed_transcribe_files
        if current_step in active_steps and queue_position < total_transcribe_files:
            queue_position += 1

        failure_rate = (stats.get('failed', 0) / completed_transcribe_files * 100.0) if completed_transcribe_files > 0 else 0.0
        meta_line = (
            f"Meta: Speed {speed_text} | Trend {trend_text} | "
            f"Queue {queue_position}/{total_transcribe_files} | Fail {failure_rate:.1f}% | "
            f"Avg WPM {avg_wpm:.1f} | ETA confidence {confidence}"
        )

        self.app.root.after(0, lambda: self.metrics_current_file_label.config(text=current_line))
        self.app.root.after(0, lambda: self.metrics_total_progress_label.config(text=total_line))
        self.app.root.after(0, lambda: self.metrics_meta_label.config(text=meta_line))
        self._schedule_metrics_refresh()
    
    def cancel_batch(self):
        """Cancel batch processing."""
        if messagebox.askyesno("Cancel", "Cancel batch processing?"):
            self.batch_state = "Canceling"
            self.app.batch_processor.cancel()
            self.cancel_btn.config(state="disabled")
    
    def _reset_ui(self):
        """Reset UI after processing."""
        self._close_batch_log_file()
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.current_progress.stop()
        self.status.set("Ready")
        self.batch_state = "Idle"
        self._stop_metrics_refresh()
    
    def log(self, message):
        """Add message to log."""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        self.app.root.after(0, lambda: self.log_text.insert(tk.END, log_msg))
        self.app.root.after(0, lambda: self.log_text.see(tk.END))
        self._write_batch_log_file(message)

    def _open_batch_log_file(self):
        """Open a per-run timestamped batch log file in the output directory."""
        if self._batch_log_file_handle is not None:
            return

        if not self.output_folder:
            return

        os.makedirs(self.output_folder, exist_ok=True)
        file_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._batch_log_file_path = os.path.join(self.output_folder, f"_batch_log_{file_stamp}.txt")
        self._batch_log_file_handle = open(self._batch_log_file_path, 'a', encoding='utf-8', buffering=1)

        self._write_batch_log_file("=" * 80)
        self._write_batch_log_file("Batch file logging enabled")
        self._write_batch_log_file(f"Log path: {self._batch_log_file_path}")
        self._write_batch_log_file("=" * 80)
        self.log(f"📝 Batch log file: {self._batch_log_file_path}")

    def _write_batch_log_file(self, message):
        """Write a message to the batch run log file if enabled."""
        if self._batch_log_file_handle is None:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._batch_log_lock:
            self._batch_log_file_handle.write(f"[{timestamp}] {message}\n")
            self._batch_log_file_handle.flush()

    def _close_batch_log_file(self):
        """Close the active batch run log file safely."""
        if self._batch_log_file_handle is not None:
            with self._batch_log_lock:
                try:
                    self._batch_log_file_handle.flush()
                    self._batch_log_file_handle.close()
                except Exception:
                    pass

        self._batch_log_file_handle = None
        self._batch_log_file_path = None
    
    def clear_log(self):
        """Clear log."""
        self.log_text.delete("1.0", tk.END)
    
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
    
    def show_skip_existing_help(self):
        """Show help dialog for skip existing feature."""
        help_text = (
            "Skip Existing Transcripts\n\n"
            "Controls whether to re-process files that already have transcripts.\n\n"
            "When enabled:\n"
            "  • Checks if a .txt file already exists for each audio file\n"
            "  • Skips files that have been previously transcribed\n"
            "  • Saves processing time on large batches\n\n"
            "When disabled:\n"
            "  • Processes all audio files, even if transcripts exist\n"
            "  • Overwrites existing transcript files\n\n"
            "Use Case:\n"
            "  • Enable to add new files to a partially processed folder\n"
            "  • Disable to regenerate all transcripts with new settings"
        )
        messagebox.showinfo("Skip Existing Help", help_text, parent=self.frame)
    
    def show_summary_help(self):
        """Show help dialog for summary report feature."""
        help_text = (
            "Create Summary Report\n\n"
            "Generates a detailed summary file after batch processing completes.\n\n"
            "Summary file contents:\n"
            "  • Total files processed and skipped\n"
            "  • Total processing time\n"
            "  • List of all processed files with status\n"
            "  • Any errors or warnings encountered\n\n"
            "File location:\n"
            "  • Saved in output folder as '_batch_summary.txt'\n"
            "  • Timestamped for reference\n\n"
            "Useful for:\n"
            "  • Tracking batch processing history\n"
            "  • Verifying all files were processed\n"
            "  • Identifying any issues during processing"
        )
        messagebox.showinfo("Summary Report Help", help_text, parent=self.frame)
    
    def show_preserve_structure_help(self):
        """Show help dialog for preserve folder structure feature."""
        help_text = (
            "Preserve Folder Structure\n\n"
            "Maintains the original directory hierarchy in the output folder.\n\n"
            "When enabled:\n"
            "  • Recreates input folder structure in output location\n"
            "  • Example: input/2024/january/file.mp3\n"
            "    → output/2024/january/file.txt\n\n"
            "When disabled:\n"
            "  • All transcripts are saved directly in output folder\n"
            "  • Example: input/2024/january/file.mp3\n"
            "    → output/file.txt\n\n"
            "Use Case:\n"
            "  • Enable when organizing files by date or category\n"
            "  • Disable for a flat output structure\n\n"
            "Note: Works best with 'Recursive' option enabled."
        )
        messagebox.showinfo("Folder Structure Help", help_text, parent=self.frame)
    
    def show_recursive_help(self):
        """Show help dialog for recursive search feature."""
        help_text = (
            "Recursively Check for Audio Files\n\n"
            "Controls whether to search subdirectories for audio files.\n\n"
            "When enabled:\n"
            "  • Searches input folder and all subdirectories\n"
            "  • Finds audio files at any depth\n"
            "  • Example: processes files in input/, input/2024/, input/2024/jan/, etc.\n\n"
            "When disabled:\n"
            "  • Only processes files directly in input folder\n"
            "  • Ignores subdirectories\n"
            "  • Example: only processes files in input/\n\n"
            "Use Case:\n"
            "  • Enable for organized hierarchical folders\n"
            "  • Disable when all files are in one location\n\n"
            "Tip: Combine with 'Preserve folder structure' to maintain organization."
        )
        messagebox.showinfo("Recursive Search Help", help_text, parent=self.frame)
    
    def show_timestamp_help(self):
        """Show help dialog for timestamp feature."""
        help_text = (
            "Timestamp Options\n\n"
            "Adds timestamps at regular intervals throughout transcripts.\n\n"
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

    def show_batch_log_file_help(self):
        """Show help dialog for timestamped batch log file option."""
        help_text = (
            "Create Timestamped Batch Log File\n\n"
            "Writes a detailed timestamped log for each batch run.\n\n"
            "When enabled:\n"
            "  - Creates a new log file in the output folder\n"
            "  - File name format: _batch_log_YYYYMMDD_HHMMSS.txt\n"
            "  - Captures run events, progress updates, and errors\n"
            "  - Keeps previous batch logs for history\n\n"
            "Use this for troubleshooting failed runs or auditing what happened."
        )
        messagebox.showinfo("Batch Log File Help", help_text, parent=self.frame)

    def show_crash_telemetry_help(self):
        """Show help dialog for crash telemetry snapshots option."""
        help_text = (
            "Crash Telemetry Snapshots\n\n"
            "Logs lightweight process memory snapshots every N completed files.\n\n"
            "What gets logged:\n"
            "  - Process RSS memory (MB)\n"
            "  - CUDA memory allocated/reserved/peak (if GPU active)\n"
            "  - CUDA free/total memory when available\n\n"
            "Why this helps:\n"
            "  - Shows whether memory climbs before hard crashes\n"
            "  - Helps distinguish app-level issues from GPU/runtime instability\n\n"
            "Notes:\n"
            "  - Disabled by default\n"
            "  - Writes to the same batch log output stream\n"
            "  - Lower intervals create more log lines"
        )
        messagebox.showinfo("Crash Telemetry Help", help_text, parent=self.frame)
    
    def _on_timestamp_toggle(self):
        """Handle timestamp checkbox toggle."""
        state = "readonly" if self.timestamps_enabled.get() else "disabled"
        self.format_combo.config(state=state)
        self.interval_combo.config(state=state)
        self.app.save_config()
    
    def _on_diarization_toggle(self):
        """Handle diarization checkbox toggle."""
        if hasattr(self, 'speakers_spinbox'):
            state = "normal" if self.diarization_enabled.get() else "disabled"
            self.speakers_spinbox.config(state=state)
        if hasattr(self, 'diarization_timestamp_combo'):
            mode_state = "readonly" if self.diarization_enabled.get() else "disabled"
            self.diarization_timestamp_combo.config(state=mode_state)
            self.app.save_config()
    
    def show_diarization_help(self):
        """Show help dialog for speaker diarization feature."""
        help_text = (
            "Speaker Diarization (Batch Processing)\n\n"
            "Automatically identifies and labels different speakers in all audio files.\n\n"
            "How it works:\n"
            "  • Analyzes voice characteristics to distinguish speakers\n"
            "  • Labels each segment with SPEAKER_00, SPEAKER_01, etc.\n"
            "  • Works best with 2-5 distinct speakers\n\n"
            "Number of Speakers:\n"
            "  • 0 (auto-detect): Let the AI determine speaker count for each file\n"
            "  • 1-10: Apply same speaker count to all files in batch\n\n"
            "Requirements:\n"
            "  • Hugging Face token configured in Model Configuration tab\n"
            "  • pyannote.audio library installed\n"
            "  • Increases processing time significantly (0.5-2x per file)\n\n"
            "Performance Impact:\n"
            "  • Diarization model loaded once, reused for all files\n"
            "  • Processing runs on GPU if available\n"
            "  • May require additional VRAM (~ 2GB)\n\n"
            "Note: All files in batch will use the same diarization settings."
        )
        messagebox.showinfo("Speaker Diarization Help", help_text, parent=self.frame)
    
    def get_config(self):
        """Get tab configuration."""
        return {
            'input_folder': self.input_folder,
            'output_folder': self.output_folder,
            'detect_date': self.detect_date.get(),
            'chars_per_line': self.chars_per_line.get(),
            'skip_existing': self.skip_existing.get(),
            'create_summary': self.create_summary.get(),
            'preserve_structure': self.preserve_structure.get(),
            'recursive': self.recursive.get(),
            'timestamps_enabled': self.timestamps_enabled.get(),
            'timestamp_format': self.timestamp_format.get(),
            'timestamp_interval': self.timestamp_interval.get(),
            'create_timestamped_log': self.create_timestamped_log.get(),
            'crash_telemetry_enabled': self.crash_telemetry_enabled.get(),
            'crash_telemetry_every_files': self.crash_telemetry_every_files.get(),
            'diarization_enabled': self.diarization_enabled.get(),
            'diarization_num_speakers': self.num_speakers.get(),
            'diarization_timestamp_mode': self.diarization_timestamp_mode.get()
        }
    
    def set_config(self, config):
        """Set tab configuration."""
        if config.get('input_folder'):
            self.input_folder = config['input_folder']
            if os.path.exists(self.input_folder):
                self.input_label.config(text=self.input_folder, foreground="black")
        
        if config.get('output_folder'):
            self.output_folder = config['output_folder']
            if os.path.exists(self.output_folder):
                self.output_label.config(text=self.output_folder, foreground="black")
        
        if 'detect_date' in config:
            self.detect_date.set(config['detect_date'])
        if 'chars_per_line' in config:
            self.chars_per_line.set(config['chars_per_line'])
        if 'skip_existing' in config:
            self.skip_existing.set(config['skip_existing'])
        if 'create_summary' in config:
            self.create_summary.set(config['create_summary'])
        if 'preserve_structure' in config:
            self.preserve_structure.set(config['preserve_structure'])
        if 'recursive' in config:
            self.recursive.set(config['recursive'])
        if 'timestamps_enabled' in config:
            self.timestamps_enabled.set(config['timestamps_enabled'])
        if 'timestamp_format' in config:
            self.timestamp_format.set(config['timestamp_format'])
        if 'timestamp_interval' in config:
            self.timestamp_interval.set(config['timestamp_interval'])
        if 'create_timestamped_log' in config:
            self.create_timestamped_log.set(config['create_timestamped_log'])
        if 'crash_telemetry_enabled' in config:
            self.crash_telemetry_enabled.set(config['crash_telemetry_enabled'])
        if 'crash_telemetry_every_files' in config:
            try:
                self.crash_telemetry_every_files.set(max(1, int(config['crash_telemetry_every_files'])))
            except (TypeError, ValueError):
                self.crash_telemetry_every_files.set(25)
        if 'diarization_enabled' in config:
            self.diarization_enabled.set(config['diarization_enabled'])
        if 'diarization_timestamp_mode' in config:
            self.diarization_timestamp_mode.set(config['diarization_timestamp_mode'])
        
        if 'num_speakers' in config:
            self.num_speakers.set(config['num_speakers'])
        
        # Update timestamp control states
        self._on_timestamp_toggle()
        
        # Update diarization control states if available
        if hasattr(self, '_on_diarization_toggle'):
            self._on_diarization_toggle()
        
        self.check_ready()
        self._update_folder_open_buttons()

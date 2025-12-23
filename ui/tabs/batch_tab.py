"""Batch processing tab - PART 1 OF 2 - See continuation comment at end"""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import time
import threading
from utilities.file_utils import FileUtils
from utilities.format_utils import FormatUtils


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
        
        # Configuration variables
        self.detect_date = tk.BooleanVar(value=True)
        self.chars_per_line = tk.IntVar(value=80)
        self.skip_existing = tk.BooleanVar(value=True)
        self.create_summary = tk.BooleanVar(value=True)
        self.preserve_structure = tk.BooleanVar(value=False)
        self.recursive = tk.BooleanVar(value=False)
        
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
        
        # Output folder
        ttk.Label(folder_frame, text="Output Folder:").grid(row=1, column=0, sticky="w", pady=5)
        output_frame = ttk.Frame(folder_frame)
        output_frame.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5)
        output_frame.columnconfigure(0, weight=1)
        
        self.output_label = ttk.Label(output_frame, text="No folder selected",
                                      foreground="gray", relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        self.output_label.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(output_frame, text="Browse", command=self.select_output).grid(row=0, column=1)
        
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
                       variable=self.recursive, command=self.app.save_config).grid(
                           row=0, column=0, sticky="w")
        ttk.Button(recursive_frame, text="?", width=3, command=self.show_recursive_help).grid(
            row=0, column=1, padx=(5, 0))
        
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
        
        # Statistics
        stats_frame = ttk.Frame(control_frame)
        stats_frame.grid(row=2, column=0, sticky="ew")
        stats_frame.columnconfigure(0, weight=1)
        
        self.stats_label = ttk.Label(stats_frame, text="Ready to process files",
                                     font=("Arial", 9, "bold"))
        self.stats_label.grid(row=0, column=0, sticky="w")
        self.eta_label = ttk.Label(stats_frame, text="", font=("Arial", 9), foreground="gray")
        self.eta_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        
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
            self.app.save_config()
    
    def select_output(self):
        """Select output folder."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_label.config(text=folder, foreground="black")
            self.log(f"📁 Output folder selected: {folder}")
            self.check_ready()
            self.app.save_config()
    
    def check_ready(self):
        """Check if batch processing is ready."""
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
        
        self.app.freeze_other_tabs(1)
        
        self.log("=" * 80)
        self.log("🚀 Starting batch transcription...")
        self.log(f"📊 Total files: {len(audio_files)}")
        self.log("=" * 80)
        
        threading.Thread(target=self._batch_worker, daemon=True).start()
    
    def _batch_worker(self):
        """Batch processing worker thread."""
        try:
            # Load model
            self.app.model_manager.load_model(
                self.app.engine.get(),
                self.app.model_size.get(),
                self.app.compute_type.get()
            )
            
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
                'compute_type': self.app.compute_type.get()
            }
            
            # Process batch
            results = self.app.batch_processor.process_batch(
                self.input_folder,
                self.output_folder,
                options,
                progress_callback=self._update_progress,
                log_callback=self.log
            )
            
            self.log("\n" + "=" * 80)
            self.log("✅ Batch processing complete!")
            self.log(f"⏱️  Total time: {FormatUtils.format_time(results['total_time'])}")
            self.log(f"✅ Successful: {results['successful']}/{results['total']}")
            if results['failed'] > 0:
                self.log(f"❌ Failed: {results['failed']}")
            self.log("=" * 80)
            
            if not self.app.batch_processor.cancel_requested:
                self.app.root.after(0, lambda: messagebox.showinfo(
                    "Batch Complete",
                    f"Successfully processed {results['successful']}/{results['total']} files"))
        
        except Exception as e:
            self.log(f"\n❌ Error: {e}")
            self.app.root.after(0, lambda e=e: messagebox.showerror("Error", f"Batch failed: {e}"))
        finally:
            self.app.model_manager.cleanup_model()
            self.app.root.after(0, self._reset_ui)
            self.app.root.after(0, self.app.unfreeze_all_tabs)
    
    def _update_progress(self, current, total, current_file):
        """Update progress."""
        self.app.root.after(0, lambda: self.overall_progress.configure(value=current))
        self.app.root.after(0, self.current_progress.start)
        
        stats = self.app.batch_processor.get_statistics()
        stats_text = (f"Processing: {current}/{total} | "
                     f"Success: {stats['successful']} | Failed: {stats['failed']}")
        self.app.root.after(0, lambda: self.stats_label.config(text=stats_text))
        
        if len(stats['processing_times']) >= 2:
            avg_time = sum(stats['processing_times']) / len(stats['processing_times'])
            remaining = total - current
            eta = avg_time * remaining
            elapsed = time.time() - self.app.batch_processor.start_time
            eta_text = f"ETA: {FormatUtils.format_time(eta)} | Elapsed: {FormatUtils.format_time(elapsed)}"
            self.app.root.after(0, lambda: self.eta_label.config(text=eta_text))
    
    def cancel_batch(self):
        """Cancel batch processing."""
        if messagebox.askyesno("Cancel", "Cancel batch processing?"):
            self.app.batch_processor.cancel()
            self.cancel_btn.config(state="disabled")
    
    def _reset_ui(self):
        """Reset UI after processing."""
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.current_progress.stop()
        self.status.set("Ready")
    
    def log(self, message):
        """Add message to log."""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        self.app.root.after(0, lambda: self.log_text.insert(tk.END, log_msg))
        self.app.root.after(0, lambda: self.log_text.see(tk.END))
    
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
            'recursive': self.recursive.get()
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
        
        self.check_ready()

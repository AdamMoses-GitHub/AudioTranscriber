"""Model configuration tab."""
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import threading
from config.constants import MODEL_SPECS, MODEL_SIZES, COMPUTE_TYPES, ENGINES
from config.environment import WHISPER_AVAILABLE, FASTER_WHISPER_AVAILABLE


class ModelConfigTab:
    """Model configuration tab UI."""
    
    def __init__(self, parent_notebook, app_controller):
        """Initialize model config tab."""
        self.parent = parent_notebook
        self.app = app_controller
        
        self.frame = ttk.Frame(parent_notebook, padding="10")
        parent_notebook.add(self.frame, text="Model Configuration")
        
        self._create_ui()
        self.update_gpu_status()
        self.update_model_info()
    
    def _create_ui(self):
        """Create UI components."""
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(3, weight=1)
        
        # Title
        ttk.Label(self.frame, text="Model Selection & Configuration",
                 font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        
        # Hardware Status
        gpu_frame = ttk.LabelFrame(self.frame, text="Hardware Status", padding="15")
        gpu_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        
        self.gpu_label = ttk.Label(gpu_frame, text="Checking GPU...", font=("Arial", 10))
        self.gpu_label.grid(row=0, column=0, sticky="w")
        
        # Library Status
        lib_frame = ttk.LabelFrame(self.frame, text="Installed Libraries", padding="15")
        lib_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        
        lib_grid = ttk.Frame(lib_frame)
        lib_grid.grid(row=0, column=0, sticky="ew")
        
        whisper_status = "✅ Installed" if WHISPER_AVAILABLE else "❌ Not Installed"
        whisper_color = "green" if WHISPER_AVAILABLE else "red"
        ttk.Label(lib_grid, text="OpenAI Whisper:", font=("Arial", 9)).grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(lib_grid, text=whisper_status, font=("Arial", 9, "bold"),
                 foreground=whisper_color).grid(row=0, column=1, sticky="w")
        
        faster_status = "✅ Installed" if FASTER_WHISPER_AVAILABLE else "❌ Not Installed"
        faster_color = "green" if FASTER_WHISPER_AVAILABLE else "red"
        ttk.Label(lib_grid, text="Faster-Whisper:", font=("Arial", 9)).grid(row=0, column=2, sticky="w", padx=(20, 10))
        ttk.Label(lib_grid, text=faster_status, font=("Arial", 9, "bold"),
                 foreground=faster_color).grid(row=0, column=3, sticky="w")
        
        if not WHISPER_AVAILABLE or not FASTER_WHISPER_AVAILABLE:
            install_text = "To install missing libraries: "
            if not WHISPER_AVAILABLE:
                install_text += "pip install openai-whisper "
            if not FASTER_WHISPER_AVAILABLE:
                install_text += "pip install faster-whisper"
            ttk.Label(lib_grid, text=install_text, font=("Arial", 8),
                     foreground="gray").grid(row=1, column=0, columnspan=4, sticky="w", pady=(5, 0))
        
        # Config notebook
        config_notebook = ttk.Notebook(self.frame)
        config_notebook.grid(row=3, column=0, sticky="nsew", pady=(0, 15))
        
        self._create_engine_tab(config_notebook)
        self._create_model_tab(config_notebook)
        self._create_compute_tab(config_notebook)
        
        # Apply button
        apply_frame = ttk.Frame(self.frame)
        apply_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        
        ttk.Label(apply_frame, text="Settings will apply to both Single File and Batch Processing modes",
                 font=("Arial", 9), foreground="gray").grid(row=0, column=0, sticky="w")
        ttk.Button(apply_frame, text="Save Configuration",
                  command=self.app.save_config).grid(row=0, column=1, padx=(10, 0))
    
    def _create_engine_tab(self, parent):
        """Create engine selection sub-tab."""
        frame = ttk.Frame(parent, padding="15")
        parent.add(frame, text="Engine Selection")
        
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        
        ttk.Label(frame,
                 text="Choose which implementation to use for transcription. Different engines have different speed/quality characteristics.",
                 font=("Arial", 9), foreground="gray", wraplength=700).grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Engine options
        container = ttk.Frame(frame)
        container.grid(row=1, column=0, sticky="nsew")
        
        ttk.Label(container, text="Select Engine:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        engines = [
            ("Faster-Whisper GPU (Recommended for GPU users)", "faster_whisper_gpu",
             FASTER_WHISPER_AVAILABLE and self.app.environment.gpu_available,
             "2-4x faster than standard Whisper on GPU"),
            ("Faster-Whisper CPU", "faster_whisper_cpu",
             FASTER_WHISPER_AVAILABLE,
             "Optimized for CPU, faster than standard Whisper"),
            ("Whisper GPU", "whisper_gpu",
             WHISPER_AVAILABLE and self.app.environment.gpu_available,
             "Original OpenAI implementation with GPU support"),
            ("Whisper CPU", "whisper_cpu",
             WHISPER_AVAILABLE,
             "Original implementation for CPU"),
            ("Auto GPU (Automatically select best available)", "auto_gpu",
             True,
             "Automatically chooses the best available GPU-accelerated engine"),
        ]
        
        for i, (text, value, available, description) in enumerate(engines):
            option_frame = ttk.Frame(container)
            option_frame.grid(row=i+1, column=0, sticky="w", pady=2)
            
            status = "✅" if available else "❌"
            rb_state = "normal" if available else "disabled"
            
            rb = ttk.Radiobutton(option_frame, text=f"{status} {text}",
                               variable=self.app.engine, value=value,
                               command=self.on_config_change, state=rb_state)
            rb.grid(row=0, column=0, sticky="w")
            
            desc_label = ttk.Label(option_frame, text=f"    → {description}",
                                  font=("Arial", 8),
                                  foreground="gray" if available else "lightgray")
            desc_label.grid(row=1, column=0, sticky="w", padx=(20, 0))
            
            if not available:
                reason = "GPU not available" if "GPU" in text and not self.app.environment.gpu_available else "Library not installed"
                ttk.Label(option_frame, text=f"    ⚠️ {reason}",
                         font=("Arial", 8), foreground="red").grid(row=2, column=0, sticky="w", padx=(20, 0))
    
    def _create_model_tab(self, parent):
        """Create model selection sub-tab."""
        frame = ttk.Frame(parent, padding="15")
        parent.add(frame, text="Model Selection")
        
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        
        # Model selector
        selector_frame = ttk.Frame(frame)
        selector_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(selector_frame, text="Model Size:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        
        model_combo = ttk.Combobox(selector_frame, textvariable=self.app.model_size,
                                   values=MODEL_SIZES, width=15, state="readonly")
        model_combo.grid(row=0, column=1, padx=(10, 0))
        model_combo.bind('<<ComboboxSelected>>', lambda e: self.on_config_change())
        
        ttk.Button(selector_frame, text="Download Selected Model",
                  command=self.download_selected).grid(row=0, column=2, padx=(20, 10))
        ttk.Button(selector_frame, text="Download All Models",
                  command=self.download_all).grid(row=0, column=3)
        
        self.download_status_label = ttk.Label(selector_frame, text="", font=("Arial", 9), foreground="gray")
        self.download_status_label.grid(row=1, column=0, columnspan=4, sticky="w", pady=(5, 0))
        
        # Model info
        info_frame = ttk.Frame(frame)
        info_frame.grid(row=2, column=0, sticky="nsew")
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)
        
        self.model_info_text = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.model_info_text.grid(row=0, column=0, sticky="nsew")
    
    def _create_compute_tab(self, parent):
        """Create compute precision sub-tab."""
        frame = ttk.Frame(parent, padding="15")
        parent.add(frame, text="Compute Precision")
        
        ttk.Label(frame,
                 text="Select the computational precision for model inference. Higher precision may improve quality but uses more memory and is slower.",
                 font=("Arial", 9), foreground="gray", wraplength=700).grid(row=0, column=0, sticky="w", pady=(0, 15))
        
        ttk.Label(frame, text="Precision Type:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(0, 10))
        
        compute_types = [
            ("float16 (Fastest, GPU only)", "float16",
             "Uses 16-bit floating point. Fastest option, requires GPU. Recommended for most GPU users."),
            ("int8 (Lower memory, slight quality loss)", "int8",
             "8-bit integer quantization. Uses less memory, slight quality trade-off. Good for large models or limited VRAM."),
            ("int8_float16 (Hybrid approach)", "int8_float16",
             "Mixed precision: int8 weights with float16 computation. Balances memory and speed.")
        ]
        
        for i, (text, value, description) in enumerate(compute_types):
            option_frame = ttk.Frame(frame)
            option_frame.grid(row=i+2, column=0, sticky="w", pady=5)
            
            available = True
            if value in ["float16", "int8_float16"] and not self.app.environment.gpu_available:
                available = False
            
            rb_state = "normal" if available else "disabled"
            
            rb = ttk.Radiobutton(option_frame, text=text, variable=self.app.compute_type, value=value,
                                command=self.on_config_change, state=rb_state)
            rb.grid(row=0, column=0, sticky="w")
            
            desc_label = ttk.Label(option_frame, text=f"    → {description}",
                                  font=("Arial", 8),
                                  foreground="gray" if available else "lightgray")
            desc_label.grid(row=1, column=0, sticky="w", padx=(20, 0))
            
            if not available:
                ttk.Label(option_frame, text="    ⚠️ GPU required",
                         font=("Arial", 8), foreground="red").grid(row=2, column=0, sticky="w", padx=(20, 0))
    
    def update_gpu_status(self):
        """Update GPU status."""
        self.gpu_label.config(text=self.app.environment.get_gpu_status_text())
    
    def update_model_info(self):
        """Update model information display."""
        model_size = self.app.model_size.get()
        specs = MODEL_SPECS.get(model_size, MODEL_SPECS["base"])
        
        whisper_dl, faster_whisper_dl = self.app.model_manager.check_model_downloaded(model_size)
        
        info_text = f"{'='*63}\n"
        info_text += f"MODEL: {model_size.upper()}\n"
        info_text += f"{'='*63}\n\n"
        
        info_text += "Download Status:\n"
        if WHISPER_AVAILABLE:
            status = "✅ Downloaded" if whisper_dl else "❌ Not Downloaded"
            info_text += f"  • Whisper:        {status}\n"
        if FASTER_WHISPER_AVAILABLE:
            status = "✅ Downloaded" if faster_whisper_dl else "❌ Not Downloaded"
            info_text += f"  • Faster-Whisper: {status}\n"
        
        if not whisper_dl and not faster_whisper_dl:
            info_text += "  💡 Will download automatically on first use\n"
        info_text += "\n"
        
        info_text += f"Parameters:        {specs['params']}\n"
        info_text += f"VRAM Required:     {specs['vram']}\n"
        info_text += f"Speed:             {specs['speed']}\n"
        info_text += f"Accuracy:          {specs['accuracy']}\n"
        info_text += f"Best For:          {specs['use_case']}\n"
        info_text += f"Download Size:     {specs['download']}\n\n"
        
        if self.app.environment.gpu_available:
            gpu_info = self.app.environment.get_gpu_info()
            info_text += f"Your GPU VRAM:     {gpu_info['memory_gb']:.1f}GB\n"
            
            if model_size == "base":
                info_text += "\n✅ RECOMMENDED: Base model offers excellent balance of speed and accuracy.\n"
            elif model_size == "tiny":
                info_text += "\n⚡ FASTEST: Great for quick drafts or testing.\n"
            elif model_size in ["large-v3", "turbo"] and gpu_info['memory_gb'] < 8:
                info_text += "\n⚠️  WARNING: This model may exceed your GPU memory.\n"
        else:
            info_text += "\n❌ No GPU detected - CPU processing will be slower\n"
            info_text += "💡 Consider 'tiny' or 'base' models for CPU usage\n"
        
        info_text += f"\n{'-'*63}\n"
        info_text += "DOWNLOAD INFORMATION:\n"
        info_text += "Models are automatically downloaded on first use.\n"
        info_text += "Cached location: ~/.cache/whisper/ (Linux/Mac)\n"
        info_text += "                 C:\\Users\\[username]\\.cache\\whisper\\ (Windows)\n"
        
        self.model_info_text.config(state="normal")
        self.model_info_text.delete("1.0", tk.END)
        self.model_info_text.insert("1.0", info_text)
        self.model_info_text.config(state="disabled")
    
    def on_config_change(self):
        """Handle configuration change."""
        self.update_model_info()
        self.app.save_config()
    
    def download_selected(self):
        """Download selected model."""
        model_size = self.app.model_size.get()
        self.download_status_label.config(text=f"Downloading {model_size} model...", foreground="blue")
        threading.Thread(target=self._download_worker, args=(model_size,), daemon=True).start()
    
    def download_all(self):
        """Download all models."""
        if not messagebox.askyesno("Download All Models",
                                   "This will download all 6 model sizes (tiny, base, small, medium, large-v3, turbo).\n"
                                   "Total download size: ~7GB\n\n"
                                   "This may take a while depending on your internet connection.\n\n"
                                   "Continue?"):
            return
        
        self.download_status_label.config(text="Downloading all models...", foreground="blue")
        threading.Thread(target=self._download_all_worker, daemon=True).start()
    
    def _download_worker(self, model_size):
        """Download model worker."""
        try:
            self.app.model_manager.download_model(
                model_size,
                self.app.engine.get(),
                self.app.compute_type.get()
            )
            self.app.root.after(0, lambda: self.download_status_label.config(
                text=f"✅ {model_size} model downloaded successfully!", foreground="green"))
            self.app.root.after(3000, lambda: self.download_status_label.config(text=""))
            self.app.root.after(0, self.update_model_info)
        except Exception as e:
            self.app.root.after(0, lambda: self.download_status_label.config(
                text=f"❌ Download failed: {str(e)}", foreground="red"))
            self.app.root.after(0, lambda e=e: messagebox.showerror("Download Error", f"Failed to download model: {e}"))
    
    def _download_all_worker(self):
        """Download all models worker."""
        failed_models = []
        
        for i, model_size in enumerate(MODEL_SIZES):
            try:
                self.app.root.after(0, lambda i=i, m=model_size: self.download_status_label.config(
                    text=f"Downloading {m} ({i+1}/{len(MODEL_SIZES)})...", foreground="blue"))
                
                self.app.model_manager.download_model(
                    model_size,
                    self.app.engine.get(),
                    self.app.compute_type.get()
                )
            except Exception as e:
                failed_models.append(f"{model_size}: {str(e)}")
        
        if len(failed_models) == 0:
            self.app.root.after(0, lambda: self.download_status_label.config(
                text=f"✅ All {len(MODEL_SIZES)} models downloaded successfully!", foreground="green"))
            self.app.root.after(0, lambda: messagebox.showinfo(
                "Download Complete",
                f"Successfully downloaded all {len(MODEL_SIZES)} models!"))
        else:
            self.app.root.after(0, lambda: self.download_status_label.config(
                text=f"⚠️ Completed with {len(failed_models)} errors", foreground="orange"))
            error_msg = "Failed models:\n" + "\n".join(failed_models)
            self.app.root.after(0, lambda: messagebox.showwarning(
                "Download Completed with Errors", error_msg))
        
        self.app.root.after(5000, lambda: self.download_status_label.config(text=""))
        self.app.root.after(0, self.update_model_info)

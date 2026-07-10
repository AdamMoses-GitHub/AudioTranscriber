"""Main application window for Audio Transcriber."""
import tkinter as tk
from tkinter import ttk
import time
from config import Environment, ConfigManager
from config.logger import get_logger
from models import ModelManager
from transcription import Transcriber, BatchProcessor, Diarizer
from ui.tabs import SingleFileTab, BatchTab, ModelConfigTab, AboutTab


logger = get_logger(__name__)


class AudioTranscriberApp:
    """Main application window."""
    
    def __init__(self, root):
        """Initialize application.
        
        Args:
            root: Tk root window.
        """
        self.root = root
        self.root.title("Audio Transcriber - Single & Batch Processing")
        self.root.geometry("1200x900")
        self.root.resizable(True, True)
        
        # Initialize core components
        self.environment = Environment()
        self.config_manager = ConfigManager()
        self.model_manager = ModelManager(self.environment)
        self.transcriber = Transcriber(self.model_manager, self.environment)
        self.batch_processor = BatchProcessor(self.transcriber, self.model_manager)
        self.diarizer = Diarizer(self.environment)
        
        # Shared configuration variables
        self.engine = tk.StringVar(value="auto_gpu")
        self.model_size = tk.StringVar(value="base")
        self.compute_type = tk.StringVar(value="float16" if self.environment.gpu_available else "int8")
        
        # Diarization variables
        self.hf_token = tk.StringVar(value="")
        self.diarization_enabled = tk.BooleanVar(value=False)
        self.num_speakers = tk.IntVar(value=0)  # 0 = auto-detect

        self._loading_config = True
        self.engine.trace_add('write', lambda *args: self.save_config())
        self.model_size.trace_add('write', lambda *args: self.save_config())
        self.compute_type.trace_add('write', lambda *args: self.save_config())
        self.hf_token.trace_add('write', lambda *args: self.save_config())
        
        # Create UI
        self._create_ui()

        # Diagnostics for unexpected app shutdown
        self.last_batch_complete_at = None
        
        # Load configuration
        self.load_config()
        self._loading_config = False
        self.save_config()
        
        # Setup window close handler
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.on_closing(source="wm_delete_window"))
        self.root.bind("<Destroy>", self._on_root_destroy_event, add="+")
    
    def _create_ui(self):
        """Create main UI."""
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Footer with quit button
        footer_frame = ttk.Frame(main_frame)
        footer_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        footer_frame.columnconfigure(0, weight=1)
        
        quit_btn = ttk.Button(footer_frame, text="Quit", command=lambda: self.on_closing(source="quit_button"))
        quit_btn.grid(row=0, column=1, sticky="e")
        
        # Create tabs
        self.single_file_tab = SingleFileTab(self.notebook, self)
        self.batch_tab = BatchTab(self.notebook, self)
        self.model_config_tab = ModelConfigTab(self.notebook, self)
        self.about_tab = AboutTab(self.notebook, self)
    
    def freeze_other_tabs(self, active_tab_index):
        """Disable all tabs except the active one during processing.
        
        Args:
            active_tab_index: Index of the active tab (0=Single File, 1=Batch, 2=Config).
        """
        for i in range(self.notebook.index('end')):
            if i != active_tab_index:
                self.notebook.tab(i, state='disabled')
    
    def unfreeze_all_tabs(self):
        """Re-enable all tabs after processing completes."""
        for i in range(self.notebook.index('end')):
            self.notebook.tab(i, state='normal')
    
    def save_config(self):
        """Save application configuration."""
        try:
            if getattr(self, '_loading_config', False):
                return

            single_file_config = {}
            if hasattr(self, 'single_file_tab') and self.single_file_tab is not None:
                single_file_config = self.single_file_tab.get_config()

            batch_config = {}
            if hasattr(self, 'batch_tab') and self.batch_tab is not None:
                batch_config = {'batch_' + k: v for k, v in self.batch_tab.get_config().items()}

            config = {
                # Engine settings
                'engine': self.engine.get(),
                'model': self.model_size.get(),
                'compute': self.compute_type.get(),
                
                # Diarization settings
                'hf_token': self.hf_token.get(),

                # Single file tab
                **single_file_config,

                # Batch tab
                **batch_config
            }
            
            self.config_manager.save(config)
        except Exception as e:
            logger.warning(f"Failed to save configuration: {e}")
    
    def load_config(self):
        """Load application configuration."""
        try:
            if self.config_manager.load():
                config = self.config_manager.get_all()
                
                # Engine settings
                if 'engine' in config:
                    self.engine.set(config['engine'])
                if 'model' in config:
                    self.model_size.set(config['model'])
                if 'compute' in config:
                    self.compute_type.set(config['compute'])
                
                # Diarization settings
                if 'hf_token' in config:
                    self.hf_token.set(config['hf_token'])
                
                # Single file tab
                single_config = {
                    'file_path': config.get('file_path'),
                    'detect_date': config.get('detect_date', True),
                    'chars_per_line': config.get('chars_per_line', 80),
                    'timestamps_enabled': config.get('timestamps_enabled', False),
                    'timestamp_format': config.get('timestamp_format', 'HH:MM:SS'),
                    'timestamp_interval': config.get('timestamp_interval', 30),
                    'single_keep_model_loaded': config.get('single_keep_model_loaded', True),
                    'diarization_enabled': config.get('diarization_enabled', False),
                    'num_speakers': config.get('diarization_num_speakers', 0),
                    'diarization_timestamp_mode': config.get('diarization_timestamp_mode', 'speaker_turns')
                }
                self.single_file_tab.set_config(single_config)
                
                # Batch tab
                batch_config = {
                    'input_folder': config.get('batch_input_folder'),
                    'output_folder': config.get('batch_output_folder'),
                    'detect_date': config.get('batch_detect_date', True),
                    'chars_per_line': config.get('batch_chars_per_line', 80),
                    'skip_existing': config.get('batch_skip_existing', True),
                    'create_summary': config.get('batch_create_summary', True),
                    'preserve_structure': config.get('batch_preserve_structure', False),
                    'recursive': config.get('batch_recursive', False),
                    'timestamps_enabled': config.get('batch_timestamps_enabled', False),
                    'timestamp_format': config.get('batch_timestamp_format', 'HH:MM:SS'),
                    'timestamp_interval': config.get('batch_timestamp_interval', 30),
                    'create_timestamped_log': config.get('batch_create_timestamped_log', False),
                    'crash_telemetry_enabled': config.get('batch_crash_telemetry_enabled', False),
                    'crash_telemetry_every_files': config.get('batch_crash_telemetry_every_files', 25),
                    'diarization_enabled': config.get('batch_diarization_enabled', False),
                    'num_speakers': config.get('batch_diarization_num_speakers', 0),
                    'diarization_timestamp_mode': config.get('batch_diarization_timestamp_mode', 'speaker_turns')
                }
                self.batch_tab.set_config(batch_config)
        except Exception as e:
            logger.warning(f"Failed to load configuration: {e}")
    
    def mark_batch_completed(self):
        """Track when batch processing completes for shutdown diagnostics."""
        self.last_batch_complete_at = time.time()
        logger.debug("Batch completed marker set at %.3f", self.last_batch_complete_at)

    def _on_root_destroy_event(self, event):
        """Log destruction of the root window for close-path diagnostics."""
        if event.widget is self.root:
            logger.debug("Root window <Destroy> event fired")

    def on_closing(self, source="unknown"):
        """Handle window closing."""
        now = time.time()
        since_batch = None
        if self.last_batch_complete_at is not None:
            since_batch = now - self.last_batch_complete_at

        logger.info(
            "on_closing invoked | source=%s | seconds_since_batch_complete=%s",
            source,
            f"{since_batch:.3f}" if since_batch is not None else "n/a"
        )

        self.save_config()
        self.root.destroy()

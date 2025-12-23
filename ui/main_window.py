"""Main application window for Audio Transcriber."""
import tkinter as tk
from tkinter import ttk
from config import Environment, ConfigManager
from models import ModelManager
from transcription import Transcriber, BatchProcessor
from ui.tabs import SingleFileTab, BatchTab, ModelConfigTab, AboutTab


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
        
        # Shared configuration variables
        self.engine = tk.StringVar(value="auto_gpu")
        self.model_size = tk.StringVar(value="base")
        self.compute_type = tk.StringVar(value="float16" if self.environment.gpu_available else "int8")
        
        # Create UI
        self._create_ui()
        
        # Load configuration
        self.load_config()
        
        # Setup window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
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
        
        quit_btn = ttk.Button(footer_frame, text="Quit", command=self.on_closing)
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
            config = {
                # Engine settings
                'engine': self.engine.get(),
                'model': self.model_size.get(),
                'compute': self.compute_type.get(),
                
                # Single file tab
                **self.single_file_tab.get_config(),
                
                # Batch tab
                **{'batch_' + k: v for k, v in self.batch_tab.get_config().items()}
            }
            
            self.config_manager.save(config)
        except Exception:
            pass
    
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
                
                # Single file tab
                single_config = {
                    'file_path': config.get('file_path'),
                    'output_path': config.get('output_path'),
                    'detect_date': config.get('detect_date', True),
                    'chars_per_line': config.get('chars_per_line', 80)
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
                    'recursive': config.get('batch_recursive', False)
                }
                self.batch_tab.set_config(batch_config)
        except Exception:
            pass
    
    def on_closing(self):
        """Handle window closing."""
        self.save_config()
        self.root.destroy()

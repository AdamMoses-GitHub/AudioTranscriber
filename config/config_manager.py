"""Configuration manager for Audio Transcriber."""
import os
import json


class ConfigManager:
    """Manages application configuration persistence."""
    
    def __init__(self, config_file=None):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to config file. If None, uses default location.
        """
        if config_file is None:
            config_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "transcriber_config.json"
            )
        self.config_file = config_file
        self.config = {}
        
    def load(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                return True
        except FileNotFoundError:
            import logging
            logging.warning(f"Config file not found: {self.config_file}")
        except json.JSONDecodeError as e:
            import logging
            logging.error(f"Invalid JSON in config file: {e}")
        except IOError as e:
            import logging
            logging.error(f"Error reading config file: {e}")
        except Exception as e:
            import logging
            logging.error(f"Unexpected error loading config: {e}")
        return False
    
    def save(self, config_dict):
        """Save configuration to file.
        
        Args:
            config_dict: Dictionary of configuration values to save.
        """
        try:
            self.config = config_dict
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2)
            return True
        except TypeError as e:
            print(f"Config contains non-serializable values: {e}")
        except IOError as e:
            print(f"Error writing config file: {e}")
        except Exception as e:
            print(f"Unexpected error saving config: {e}")
        return False
    
    def get(self, key, default=None):
        """Get configuration value.
        
        Args:
            key: Configuration key.
            default: Default value if key not found.
            
        Returns:
            Configuration value or default.
        """
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value.
        
        Args:
            key: Configuration key.
            value: Configuration value.
        """
        self.config[key] = value
    
    def get_all(self):
        """Get all configuration values."""
        return self.config.copy()

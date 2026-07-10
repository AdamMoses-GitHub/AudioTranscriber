"""Configuration manager for Audio Transcriber."""
import os
import json
import tempfile
from .logger import get_logger

logger = get_logger(__name__)


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
            logger.warning(f"Config file not found: {self.config_file}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
        except IOError as e:
            logger.error(f"Error reading config file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading config: {e}")
        return False
    
    def save(self, config_dict):
        """Save configuration to file.
        
        Args:
            config_dict: Dictionary of configuration values to save.
        """
        temp_path = None
        try:
            self.config = config_dict

            config_dir = os.path.dirname(os.path.abspath(self.config_file))
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)

            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=config_dir or None,
                delete=False,
                newline='\n'
            ) as temp_file:
                temp_path = temp_file.name
                json.dump(config_dict, temp_file, indent=2)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(temp_path, self.config_file)
            return True
        except TypeError as e:
            logger.error(f"Config contains non-serializable values: {e}")
        except IOError as e:
            logger.error(f"Error writing config file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving config: {e}")
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
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
    
    def get_hf_token(self) -> str:
        """Get Hugging Face authentication token.
        
        Returns:
            HF token string, or empty string if not set.
        """
        return self.config.get('hf_token', '')
    
    def set_hf_token(self, token: str) -> None:
        """Set Hugging Face authentication token.
        
        Note: Token is stored in plaintext in config file. For better security,
        consider using environment variables (HF_TOKEN) instead.
        
        Args:
            token: HF authentication token.
        """
        self.config['hf_token'] = token
        logger.info("HF token updated in configuration")
    
    def has_hf_token(self) -> bool:
        """Check if HF token is configured.
        
        Returns:
            True if token is set and not empty, False otherwise.
        """
        token = self.get_hf_token()
        return bool(token and token.strip())
    
    def clear_hf_token(self) -> None:
        """Clear the stored HF token from configuration."""
        if 'hf_token' in self.config:
            self.config['hf_token'] = ''
            logger.info("HF token cleared from configuration")

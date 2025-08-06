"""
Configuration module for FinCLI

Handles user configuration settings stored in ~/fin/config.json
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration manager for FinCLI."""
    
    def __init__(self, config_dir: str = None):
        """
        Initialize configuration.
        
        Args:
            config_dir: Directory for config file (default: ~/fin)
        """
        if config_dir is None:
            config_dir = os.path.expanduser("~/fin")
        
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.json"
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.config_file.exists():
            # Create default config
            default_config = {
                "auto_today_for_important": True,
                "default_editor": None,
                "default_days": 1,
                "show_sections": True,
            }
            self._save_config(default_config)
            return default_config
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If config is corrupted, recreate with defaults
            default_config = {
                "auto_today_for_important": True,
                "default_editor": None,
                "default_days": 1,
                "show_sections": True,
            }
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError:
            # Silently fail if we can't write config
            pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self._config[key] = value
        self._save_config(self._config)
    
    def get_auto_today_for_important(self) -> bool:
        """Get whether important tasks should automatically get today label."""
        return self.get("auto_today_for_important", True)
    
    def set_auto_today_for_important(self, enabled: bool) -> None:
        """Set whether important tasks should automatically get today label."""
        self.set("auto_today_for_important", enabled)
    
    def get_default_editor(self) -> str:
        """Get the default editor setting."""
        return self.get("default_editor")
    
    def set_default_editor(self, editor: str) -> None:
        """Set the default editor."""
        self.set("default_editor", editor)
    
    def get_default_days(self) -> int:
        """Get the default days setting."""
        return self.get("default_days", 1)
    
    def set_default_days(self, days: int) -> None:
        """Set the default days."""
        self.set("default_days", days)
    
    def get_show_sections(self) -> bool:
        """Get whether to show organized sections."""
        return self.get("show_sections", True)
    
    def set_show_sections(self, enabled: bool) -> None:
        """Set whether to show organized sections."""
        self.set("show_sections", enabled) 
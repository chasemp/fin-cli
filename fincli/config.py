"""
Configuration module for FinCLI

Handles user configuration settings stored in ~/fin/config.json
"""

import json
import os
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration manager for FinCLI."""

    def __init__(self, config_dir: str = None):
        """
        Initialize configuration.

        Args:
            config_dir: Directory for config file (default: ~/fin)
        """
        if config_dir is None:
            # Check for environment variable first, then fall back to default
            env_config_dir = os.environ.get("FIN_CONFIG_DIR")
            if env_config_dir:
                config_dir = env_config_dir
            else:
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
                "show_all_open_by_default": True,
                "weekdays_only_lookback": True,
                "task_title_wrap_width": 120,
                "task_date_format": "M/D",
            }
            self._save_config(default_config)
            return default_config

        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If config is corrupted, recreate with defaults
            default_config = {
                "auto_today_for_important": True,
                "default_editor": None,
                "default_days": 1,
                "show_sections": True,
                "show_all_open_by_default": True,
                "weekdays_only_lookback": True,
                "task_title_wrap_width": 120,
                "task_date_format": "M/D",
            }
            self._save_config(default_config)
            return default_config

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, "w") as f:
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

    def get_show_all_open_by_default(self) -> bool:
        """Get whether to show all open tasks by default (vs. just recent ones)."""
        return self.get("show_all_open_by_default", True)

    def set_show_all_open_by_default(self, enabled: bool) -> None:
        """Set whether to show all open tasks by default."""
        self.set("show_all_open_by_default", enabled)

    def get_weekdays_only_lookback(self) -> bool:
        """Get whether date lookback should consider only weekdays (vs. all days)."""
        return self.get("weekdays_only_lookback", True)

    def set_weekdays_only_lookback(self, enabled: bool) -> None:
        """Set whether date lookback should consider only weekdays."""
        self.set("weekdays_only_lookback", enabled)

    def get_task_title_wrap_width(self) -> int:
        """Get the width for wrapping task titles."""
        return self.get("task_title_wrap_width", 120)

    def set_task_title_wrap_width(self, width: int) -> None:
        """Set the width for wrapping task titles."""
        self.set("task_title_wrap_width", width)

    def get_task_date_format(self) -> str:
        """Get the date format for task titles."""
        return self.get("task_date_format", "M/D")

    def set_task_date_format(self, date_format: str) -> None:
        """Set the date format for task titles."""
        self.set("task_date_format", date_format)

    def get_context_default_label_filter(self, context: str = "default") -> str:
        """Get the default label filter for a specific context.

        Args:
            context: Context name (defaults to 'default')

        Returns:
            Default label filter string (e.g., "NOT backlog") or None if not set
        """
        context_filters = self.get("context_default_label_filters", {})
        return context_filters.get(context)

    def set_context_default_label_filter(self, context: str, label_filter: str) -> None:
        """Set the default label filter for a specific context.

        Args:
            context: Context name
            label_filter: Label filter string (e.g., "NOT backlog")
        """
        context_filters = self.get("context_default_label_filters", {})
        context_filters[context] = label_filter
        self.set("context_default_label_filters", context_filters)

    def remove_context_default_label_filter(self, context: str) -> None:
        """Remove the default label filter for a specific context.

        Args:
            context: Context name
        """
        context_filters = self.get("context_default_label_filters", {})
        if context in context_filters:
            del context_filters[context]
            self.set("context_default_label_filters", context_filters)

    def get_all_context_default_label_filters(self) -> dict:
        """Get all context default label filters.

        Returns:
            Dictionary mapping context names to their default label filters
        """
        return self.get("context_default_label_filters", {})

"""
Tests for the config module.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from fincli.config import Config


class TestConfig:
    """Test the Config class."""

    def test_config_creation(self):
        """Test creating a new config with defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(temp_dir)

            assert config.get_auto_today_for_important() is True
            assert config.get_show_sections() is True
            assert config.get_default_days() == 1
            assert config.get_default_editor() is None

            # Check that config file was created
            config_file = Path(temp_dir) / "config.json"
            assert config_file.exists()

            # Check config file contents
            with open(config_file, "r") as f:
                config_data = json.load(f)

            assert config_data["auto_today_for_important"] is True
            assert config_data["show_sections"] is True
            assert config_data["default_days"] == 1
            assert config_data["default_editor"] is None

    def test_config_loading(self):
        """Test loading existing config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            # Create config file with custom values
            config_data = {
                "auto_today_for_important": False,
                "show_sections": False,
                "default_days": 7,
                "default_editor": "vim",
            }

            with open(config_file, "w") as f:
                json.dump(config_data, f)

            config = Config(temp_dir)

            assert config.get_auto_today_for_important() is False
            assert config.get_show_sections() is False
            assert config.get_default_days() == 7
            assert config.get_default_editor() == "vim"

    def test_config_setting(self):
        """Test setting config values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(temp_dir)

            # Set values
            config.set_auto_today_for_important(False)
            config.set_show_sections(False)
            config.set_default_days(7)
            config.set_default_editor("vim")

            # Check values
            assert config.get_auto_today_for_important() is False
            assert config.get_show_sections() is False
            assert config.get_default_days() == 7
            assert config.get_default_editor() == "vim"

            # Check that config file was updated
            config_file = Path(temp_dir) / "config.json"
            with open(config_file, "r") as f:
                config_data = json.load(f)

            assert config_data["auto_today_for_important"] is False
            assert config_data["show_sections"] is False
            assert config_data["default_days"] == 7
            assert config_data["default_editor"] == "vim"

    def test_config_corruption_recovery(self):
        """Test recovery from corrupted config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            # Create corrupted config file
            with open(config_file, "w") as f:
                f.write("invalid json content")

            config = Config(temp_dir)

            # Should recover with defaults
            assert config.get_auto_today_for_important() is True
            assert config.get_show_sections() is True
            assert config.get_default_days() == 1
            assert config.get_default_editor() is None

    def test_config_get_set_generic(self):
        """Test generic get/set methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(temp_dir)

            # Test get with default
            assert config.get("nonexistent", "default") == "default"

            # Test set and get
            config.set("custom_key", "custom_value")
            assert config.get("custom_key") == "custom_value"

            # Test get without default
            assert config.get("nonexistent") is None

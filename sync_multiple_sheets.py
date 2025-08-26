#!/usr/bin/env python3
"""
Multi-source Google Sheets sync script for fin-cli.

This script can sync multiple Google Sheets sources based on a configuration file.
It's designed to be run via cron or manually to keep all configured sources in sync.

Usage:
    python sync_multiple_sheets.py [options]
    python sync_multiple_sheets.py --help

Configuration:
    Uses sync_config.yaml for source configuration and settings.
    See sync_config.yaml.example for configuration format.

Environment Variables:
    SYNC_CONFIG_PATH: Path to configuration file (default: sync_config.yaml)
    LOG_LEVEL: Logging level (optional, overrides config)
"""

import argparse
import logging
import os
from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List

import yaml

# Add the project root to the Python path so we can import fincli modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from fincli.config import Config
    from fincli.db import DatabaseManager
    from fincli.sheets_connector import create_sheets_reader_from_token
    from fincli.sync_engine import SyncEngine
    from fincli.sync_strategies import RemoteSystemType, SyncStrategyFactory
    from fincli.tasks import TaskManager
except ImportError as e:
    print(f"❌ Error importing fincli modules: {e}")
    print("   Make sure you're running this script from the fin-cli project root")
    sys.exit(1)


def setup_logging(log_level: str = "INFO", log_file: str = "sync_multiple_sheets.log") -> None:
    """Set up logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    logging.basicConfig(level=numeric_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(log_file)])


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        if not config:
            raise ValueError("Configuration file is empty")

        return config
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        print("   Create sync_config.yaml or specify a different path with --config")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ Error parsing configuration file: {e}")
        sys.exit(1)


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate the configuration structure."""
    required_sections = ["global", "sources"]

    for section in required_sections:
        if section not in config:
            print(f"❌ Missing required configuration section: {section}")
            return False

    if not config["sources"]:
        print("❌ No sources configured in configuration file")
        return False

    # Validate each source
    for source_name, source_config in config["sources"].items():
        required_fields = ["sheet_id", "sheet_name", "enabled"]
        for field in required_fields:
            if field not in source_config:
                print(f"❌ Source '{source_name}' missing required field: {field}")
                return False

        if source_config["enabled"] and not source_config["sheet_id"]:
            print(f"❌ Source '{source_name}' is enabled but has no sheet_id")
            return False

    return True


def sync_single_source(source_name: str, source_config: Dict[str, Any], global_config: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Sync a single Google Sheets source."""
    start_time = time.time()
    logger.info(f"🔄 Starting sync for source: {source_name}")

    try:
        # Get configuration with fallbacks to global settings
        sheet_id = source_config["sheet_id"]
        sheet_name = source_config.get("sheet_name", "todo")
        purge_after_import = source_config.get("purge_after_import", global_config.get("purge_after_import", True))
        dry_run = source_config.get("dry_run", global_config.get("dry_run", False))

        # Get token path (source-specific or global)
        token_path = source_config.get("google_token_path", global_config.get("google_token_path", "~/.fin/google_token.json"))
        token_path = os.path.expanduser(token_path)

        if not os.path.exists(token_path):
            raise FileNotFoundError(f"Google token file not found: {token_path}")

        # Set environment variables for fin-cli modules
        if global_config.get("fin_db_path"):
            os.environ["FIN_DB_PATH"] = global_config["fin_db_path"]
        if global_config.get("fin_config_dir"):
            os.environ["FIN_CONFIG_DIR"] = global_config["fin_config_dir"]

        # Create sheets reader
        logger.info(f"📖 Creating Google Sheets reader for {source_name}...")
        sheets_reader = create_sheets_reader_from_token(token_path, sheet_id)

        # Create database and task managers
        logger.info(f"🗄️  Initializing database for {source_name}...")
        db_manager = DatabaseManager()
        task_manager = TaskManager(db_manager)
        sync_engine = SyncEngine(db_manager, task_manager)

        # Create sync strategy
        logger.info(f"🔄 Creating sync strategy for {source_name}...")
        strategy = SyncStrategyFactory.create_strategy(RemoteSystemType.GOOGLE_SHEETS, sync_engine, sheets_reader=sheets_reader)

        # Validate sheet structure
        logger.info(f"✅ Validating sheet structure for {source_name}...")
        validation_result = strategy.validate_sheet_structure(sheet_name)

        if not validation_result["valid"]:
            raise ValueError(f"Sheet validation failed: {validation_result['error']}")

        logger.info(f"✅ Sheet structure validated for {source_name}")
        logger.info(f"   • Total rows: {validation_result['total_rows']}")
        logger.info(f"   • Valid tasks found: {validation_result['valid_tasks_found']}")

        # Perform sync
        logger.info(f"🔄 Starting sync for {source_name}...")
        sync_result = strategy.sync_sheet_tasks(sheet_name=sheet_name, dry_run=dry_run, purge_after_import=purge_after_import)

        if not sync_result["success"]:
            raise RuntimeError(f"Sync failed: {sync_result['error']}")

        # Calculate duration
        duration = time.time() - start_time

        # Prepare result summary
        result = {"source_name": source_name, "success": True, "duration": duration, "sync_result": sync_result, "error": None}

        logger.info(f"✅ Sync completed for {source_name} in {duration:.2f}s")
        logger.info(f"   • Tasks imported: {sync_result.get('tasks_imported', 0)}")
        logger.info(f"   • Tasks updated: {sync_result.get('tasks_updated', 0)}")
        logger.info(f"   • Tasks skipped: {sync_result.get('tasks_skipped', 0)}")

        if "purge_results" in sync_result:
            purge = sync_result["purge_results"]
            logger.info(f"   • Remote tasks purged: {purge.get('tasks_purged', 0)}")

        return result

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ Sync failed for {source_name} after {duration:.2f}s: {str(e)}")

        return {"source_name": source_name, "success": False, "duration": duration, "sync_result": None, "error": str(e)}


def main():
    """Main multi-source sync function."""
    parser = argparse.ArgumentParser(description="Sync multiple Google Sheets sources to fin-cli", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)

    parser.add_argument("--config", "-c", default="sync_config.yaml", help="Path to configuration file")
    parser.add_argument("--source", "-s", help="Sync only the specified source")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level (overrides config)")
    parser.add_argument("--log-file", help="Log file path (overrides config)")

    args = parser.parse_args()

    # Load configuration
    config_path = os.environ.get("SYNC_CONFIG_PATH", args.config)
    config = load_config(config_path)

    # Validate configuration
    if not validate_config(config):
        sys.exit(1)

    # Set up logging
    log_level = args.log_level or config["global"].get("log_level", "INFO")
    log_file = args.log_file or "sync_multiple_sheets.log"
    setup_logging(log_level, log_file)
    logger = logging.getLogger(__name__)

    logger.info("🚀 Starting multi-source Google Sheets sync")
    logger.info(f"   • Configuration file: {config_path}")
    logger.info(f"   • Log level: {log_level}")

    # Override global settings with command line arguments
    if args.dry_run:
        config["global"]["dry_run"] = True
        logger.info("   • Dry run mode: enabled")

    if args.verbose:
        config["global"]["verbose"] = True
        logger.info("   • Verbose mode: enabled")

    # Filter sources
    sources_to_sync = {}
    if args.source:
        if args.source not in config["sources"]:
            logger.error(f"❌ Source '{args.source}' not found in configuration")
            sys.exit(1)
        sources_to_sync[args.source] = config["sources"][args.source]
        logger.info(f"   • Single source mode: {args.source}")
    else:
        # Get enabled sources
        sources_to_sync = {name: source_config for name, source_config in config["sources"].items() if source_config.get("enabled", False)}
        logger.info(f"   • Sources to sync: {', '.join(sources_to_sync.keys())}")

    if not sources_to_sync:
        logger.warning("⚠️  No enabled sources found")
        sys.exit(0)

    # Add random delay if configured
    random_delay_range = config.get("schedule", {}).get("random_delay_range", [0, 0])
    if random_delay_range[1] > 0:
        delay = random.uniform(random_delay_range[0], random_delay_range[1])
        logger.info(f"⏰ Adding random delay: {delay:.1f}s")
        time.sleep(delay)

    # Sync each source
    results = []
    start_time = time.time()

    for source_name, source_config in sources_to_sync.items():
        if not source_config.get("enabled", False):
            logger.info(f"⏭️  Skipping disabled source: {source_name}")
            continue

        result = sync_single_source(source_name, source_config, config["global"], logger)
        results.append(result)

        # Add delay between sources to avoid overwhelming the API
        if len(results) < len(sources_to_sync):
            delay = 5  # 5 second delay between sources
            logger.info(f"⏰ Waiting {delay}s before next source...")
            time.sleep(delay)

    # Summary
    total_duration = time.time() - start_time
    successful_syncs = sum(1 for r in results if r["success"])
    failed_syncs = len(results) - successful_syncs

    logger.info("📊 Sync Summary")
    logger.info(f"   • Total sources: {len(sources_to_sync)}")
    logger.info(f"   • Successful: {successful_syncs}")
    logger.info(f"   • Failed: {failed_syncs}")
    logger.info(f"   • Total duration: {total_duration:.2f}s")

    if failed_syncs > 0:
        logger.error("❌ Some syncs failed:")
        for result in results:
            if not result["success"]:
                logger.error(f"   • {result['source_name']}: {result['error']}")
        sys.exit(1)
    else:
        logger.info("🎉 All syncs completed successfully!")


if __name__ == "__main__":
    main()

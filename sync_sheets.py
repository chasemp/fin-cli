#!/usr/bin/env python3
"""
Standalone Google Sheets sync script for fin-cli.

This script can be run independently or scheduled via cron to sync tasks
from Google Sheets into the local fin-cli database.

Usage:
    python sync_sheets.py [options]
    python sync_sheets.py --help

Environment Variables:
    SHEET_ID: Google Sheet ID (required)
    FIN_DB_PATH: Path to fin-cli database (optional)
    FIN_CONFIG_DIR: Path to fin-cli config directory (optional)
    GOOGLE_TOKEN_PATH: Path to Google OAuth token (optional)
    LOG_LEVEL: Logging level (optional, default: INFO)
"""

import argparse
import logging
import os
from pathlib import Path
import sys

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


def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    logging.basicConfig(level=numeric_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("sync_sheets.log")])


def get_config() -> dict:
    """Get configuration from environment variables and defaults."""
    config = {"sheet_id": os.environ.get("SHEET_ID"), "sheet_name": os.environ.get("SHEET_NAME", "todo"), "token_path": os.environ.get("GOOGLE_TOKEN_PATH", "~/.fin/google_token.json"), "db_path": os.environ.get("FIN_DB_PATH"), "config_dir": os.environ.get("FIN_CONFIG_DIR", "~/.fin"), "purge_after_import": os.environ.get("PURGE_AFTER_IMPORT", "true").lower() == "true", "dry_run": os.environ.get("DRY_RUN", "false").lower() == "true", "verbose": os.environ.get("VERBOSE", "false").lower() == "true"}

    # Expand user paths
    config["token_path"] = os.path.expanduser(config["token_path"])
    config["config_dir"] = os.path.expanduser(config["config_dir"])

    return config


def validate_config(config: dict) -> bool:
    """Validate the configuration."""
    if not config["sheet_id"]:
        print("❌ Error: SHEET_ID environment variable is required")
        print("   Set SHEET_ID to your Google Sheet ID")
        return False

    if not os.path.exists(config["token_path"]):
        print(f"❌ Error: Google token file not found: {config['token_path']}")
        print("   Run gcreds.py first to authenticate with Google")
        return False

    return True


def main():
    """Main sync function."""
    parser = argparse.ArgumentParser(description="Sync tasks from Google Sheets to fin-cli", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)

    parser.add_argument("--sheet-id", help="Google Sheet ID (overrides SHEET_ID env var)")
    parser.add_argument("--sheet-name", default="todo", help="Sheet name to sync from (default: todo)")
    parser.add_argument("--token-path", help="Path to Google OAuth token (overrides GOOGLE_TOKEN_PATH env var)")
    parser.add_argument("--db-path", help="Path to fin-cli database (overrides FIN_DB_PATH env var)")
    parser.add_argument("--config-dir", help="Path to fin-cli config directory (overrides FIN_CONFIG_DIR env var)")
    parser.add_argument("--purge-after-import", action="store_true", help="Purge remote tasks after import")
    parser.add_argument("--no-purge", action="store_true", help="Don't purge remote tasks after import")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Get configuration
    config = get_config()

    # Override with command line arguments
    if args.sheet_id:
        config["sheet_id"] = args.sheet_id
    if args.sheet_name:
        config["sheet_name"] = args.sheet_name
    if args.token_path:
        config["token_path"] = args.token_path
    if args.db_path:
        config["db_path"] = args.db_path
    if args.config_dir:
        config["config_dir"] = args.config_dir
    if args.purge_after_import:
        config["purge_after_import"] = True
    if args.no_purge:
        config["purge_after_import"] = False
    if args.dry_run:
        config["dry_run"] = True
    if args.verbose:
        config["verbose"] = True

    # Validate configuration
    if not validate_config(config):
        sys.exit(1)

    # Set environment variables for fin-cli modules
    if config["db_path"]:
        os.environ["FIN_DB_PATH"] = config["db_path"]
    if config["config_dir"]:
        os.environ["FIN_CONFIG_DIR"] = config["config_dir"]

    logger.info("🚀 Starting Google Sheets sync")
    logger.info(f"   • Sheet ID: {config['sheet_id']}")
    logger.info(f"   • Sheet name: {config['sheet_name']}")
    logger.info(f"   • Token path: {config['token_path']}")
    logger.info(f"   • Purge after import: {config['purge_after_import']}")
    logger.info(f"   • Dry run: {config['dry_run']}")
    logger.info(f"   • Verbose: {config['verbose']}")

    try:
        # Create sheets reader
        logger.info("📖 Creating Google Sheets reader...")
        sheets_reader = create_sheets_reader_from_token(config["token_path"], config["sheet_id"])

        # Create database and task managers
        logger.info("🗄️  Initializing database...")
        db_manager = DatabaseManager()
        task_manager = TaskManager(db_manager)
        sync_engine = SyncEngine(db_manager, task_manager)

        # Create sync strategy
        logger.info("🔄 Creating sync strategy...")
        strategy = SyncStrategyFactory.create_strategy(RemoteSystemType.GOOGLE_SHEETS, sync_engine, sheets_reader=sheets_reader)

        # Validate sheet structure
        logger.info(f"✅ Validating sheet structure for '{config['sheet_name']}'...")
        validation_result = strategy.validate_sheet_structure(config["sheet_name"])

        if not validation_result["valid"]:
            logger.error(f"❌ Sheet validation failed: {validation_result['error']}")
            if "missing_headers" in validation_result:
                logger.error(f"   Missing headers: {', '.join(validation_result['missing_headers'])}")
                logger.error(f"   Found headers: {', '.join(validation_result['found_headers'])}")
            sys.exit(1)

        logger.info("✅ Sheet structure validated successfully")
        logger.info(f"   • Total rows: {validation_result['total_rows']}")
        logger.info(f"   • Valid tasks found: {validation_result['valid_tasks_found']}")

        # Perform sync
        logger.info("🔄 Starting sync...")
        sync_result = strategy.sync_sheet_tasks(sheet_name=config["sheet_name"], dry_run=config["dry_run"], purge_after_import=config["purge_after_import"])

        if not sync_result["success"]:
            logger.error(f"❌ Sync failed: {sync_result['error']}")
            sys.exit(1)

        # Display results
        if config["dry_run"]:
            logger.info("🔍 DRY RUN RESULTS (no changes made):")
        else:
            logger.info("✅ Sync completed successfully:")

        logger.info(f"   • Total rows in sheet: {sync_result['total_rows']}")
        logger.info(f"   • Tasks imported: {sync_result.get('tasks_imported', 0)}")
        logger.info(f"   • Tasks updated: {sync_result.get('tasks_updated', 0)}")
        logger.info(f"   • Tasks skipped: {sync_result.get('tasks_skipped', 0)}")

        if "purge_results" in sync_result:
            purge = sync_result["purge_results"]
            logger.info(f"   • Remote tasks purged: {purge.get('tasks_purged', 0)}")
            if purge.get("errors"):
                logger.error(f"   • Purge errors: {len(purge['errors'])}")
                for error in purge["errors"]:
                    logger.error(f"     - {error}")

        if config["verbose"] and "errors" in sync_result and sync_result["errors"]:
            logger.info(f"   • Sync errors: {len(sync_result['errors'])}")
            for error in sync_result["errors"]:
                logger.error(f"     - {error}")

        logger.info("🎉 Google Sheets sync completed successfully!")

    except Exception as e:
        logger.error(f"❌ Error during sync: {str(e)}")
        if config["verbose"]:
            import traceback

            logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

# Google Sheets Sync for fin-cli

This document describes how to use the Google Sheets sync functionality in fin-cli, which allows you to automatically import tasks from Google Sheets into your local task database.

## Overview

The Google Sheets sync system provides:

- **Automatic task import** from Google Sheets to fin-cli
- **Dual authority model** supporting different sync strategies
- **CLI integration** with `fin sync-sheets` and `fin sync-status` commands
- **Standalone scripts** for automation and cron jobs
- **Multi-source support** for managing multiple Google Sheets
- **Comprehensive logging** and error handling

## Architecture

### Dual Authority Model

The system supports two types of remote task authority:

1. **Full Authority** (e.g., Google Sheets)
   - Local fin-cli is authoritative for both task definition and status
   - Remote tasks are purged after import to prevent duplication
   - Tasks get `#remote` tag and `authority:full` label

2. **Status Only Authority** (e.g., Confluence)
   - Remote system is authoritative for task definition
   - Local fin-cli is authoritative for task status
   - Tasks become "shadow tasks" with `#remote #shadow` tags
   - Tasks get `authority:status` label

### Components

- **`SheetsReader`**: Reads and parses Google Sheets data
- **`SyncEngine`**: Core synchronization logic
- **`GoogleSheetsSyncStrategy`**: Google Sheets-specific sync behavior
- **`TaskMapper`**: Maps remote tasks to local format
- **`RemoteTaskValidator`**: Validates remote task data

## Quick Start

### 1. Initial Setup

First, authenticate with Google and get your OAuth token:

```bash
# Run the authentication script
python gcreds.py

# This will create ~/.fin/google_token.json
```

### 2. Basic CLI Usage

Use the built-in CLI commands:

```bash
# Sync from Google Sheets
fin sync-sheets --sheet-id "YOUR_SHEET_ID" --verbose

# Check sync status
fin sync-status --verbose

# Dry run to see what would be synced
fin sync-sheets --sheet-id "YOUR_SHEET_ID" --dry-run --verbose
```

### 3. Standalone Script

For automation, use the standalone script:

```bash
# Set environment variables
export SHEET_ID="YOUR_SHEET_ID"
export GOOGLE_TOKEN_PATH="~/.fin/google_token.json"

# Run sync
python sync_sheets.py --verbose
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SHEET_ID` | Google Sheet ID (required) | None |
| `SHEET_NAME` | Sheet name to sync from | "todo" |
| `GOOGLE_TOKEN_PATH` | Path to OAuth token | "~/.fin/google_token.json" |
| `FIN_DB_PATH` | Path to fin-cli database | Auto-detected |
| `FIN_CONFIG_DIR` | Path to fin-cli config | "~/.fin" |
| `PURGE_AFTER_IMPORT` | Purge remote tasks | "true" |
| `DRY_RUN` | Show changes without applying | "false" |
| `VERBOSE` | Show detailed output | "false" |
| `LOG_LEVEL` | Logging level | "INFO" |

### Google Sheet Format

Your Google Sheet must have these columns (case-insensitive):

| Column | Required | Description |
|--------|----------|-------------|
| `RunID` | Yes | Unique task identifier |
| `User Name` | Yes | User who created the task |
| `Text` | Yes | Task description |
| `Source` | Yes | Source system identifier |
| `Ts Time` | No | Timestamp (optional) |
| `Permalink` | No | Link to original (optional) |

**Example Sheet Structure:**
```
| Ts Time      | User Name | Text           | Permalink           | RunID  | Source        |
|--------------|-----------|----------------|---------------------|--------|---------------|
| 2025-01-15   | John Doe  | Fix login bug  | http://example.com  | RUN001 | google_sheets |
| 2025-01-16   | Jane Smith| Add new feature| http://example2.com | RUN002 | google_sheets |
```

## Advanced Usage

### Multi-Source Configuration

Create `sync_config.yaml` for managing multiple sources:

```yaml
global:
  purge_after_import: true
  dry_run: false
  log_level: INFO

sources:
  main_project:
    sheet_id: "1TWob-vh6qZ1rzUNN1GMAxDl87UwH5P5ngyh2THeLcGo"
    sheet_name: "todo"
    description: "Main project tasks"
    purge_after_import: true
    enabled: true
    
  team_tasks:
    sheet_id: "YOUR_TEAM_SHEET_ID"
    sheet_name: "tasks"
    description: "Team collaboration"
    purge_after_import: false
    enabled: true
```

### Multi-Source Sync

```bash
# Sync all enabled sources
python sync_multiple_sheets.py --verbose

# Sync specific source
python sync_multiple_sheets.py --source main_project --verbose

# Dry run
python sync_multiple_sheets.py --dry-run --verbose
```

### Automation with Cron

Set up automatic syncing:

```bash
# Make setup script executable
chmod +x setup_cron.sh

# Run setup
./setup_cron.sh

# Or manually add to crontab
# Every 30 minutes:
*/30 * * * * cd /path/to/fin-cli && python3 sync_multiple_sheets.py >> sync.log 2>&1
```

## Task Mapping and Labels

### Automatic Labels

Tasks automatically get these labels:

- `source:{remote_source}` - Identifies the source system
- `authority:{authority_type}` - Shows authority level (full/status)
- `#remote` - Marks tasks as imported from remote system
- `#shadow` - Added for status-only authority tasks

### Example Task

After import, a task might look like:

```
✅ Fix login bug [source:google_sheets, authority:full, #remote]
```

## Monitoring and Troubleshooting

### Log Files

- `sync_sheets.log` - Single source sync logs
- `sync_multiple_sheets.log` - Multi-source sync logs
- `sync.log` - Cron job output (if using cron)

### Common Issues

#### Authentication Errors

```bash
❌ Error: Google token file not found: ~/.fin/google_token.json
   Run gcreds.py first to authenticate with Google
```

**Solution:** Run `python gcreds.py` to authenticate and create the token file.

#### Sheet Structure Errors

```bash
❌ Sheet validation failed: Missing required headers: ['runid', 'user_name']
   Found headers: ['Timestamp', 'User', 'Description', 'ID']
```

**Solution:** Ensure your sheet has the required columns with correct names.

#### API Rate Limits

```bash
❌ Error during sync: Quota exceeded
```

**Solution:** Add delays between syncs or reduce sync frequency.

### Health Checks

Check sync status:

```bash
# Overall status
fin sync-status --verbose

# Source-specific status
fin sync-status --source google_sheets --verbose
```

## Performance and Best Practices

### API Rate Limits

- Google Sheets API has quotas (1000 requests per 100 seconds per user)
- Use reasonable sync intervals (15+ minutes recommended)
- Add random delays between syncs to avoid rate limits

### Database Performance

- Large numbers of remote tasks may impact performance
- Consider purging old remote tasks periodically
- Monitor database size and performance

### Error Handling

- Failed syncs are logged with detailed error information
- Retry logic with exponential backoff
- Notifications for critical failures (configurable)

## Security Considerations

### OAuth Token Security

- Store OAuth tokens securely (`~/.fin/google_token.json`)
- Use appropriate file permissions (600 recommended)
- Rotate tokens periodically

### Data Privacy

- Remote task data is stored locally
- Consider data retention policies
- Be aware of what data is being imported

### Access Control

- Limit who can access the sync configuration
- Use separate OAuth tokens for different environments
- Monitor sync logs for unauthorized access

## Troubleshooting Guide

### Sync Not Working

1. **Check authentication:**
   ```bash
   python gcreds.py
   ```

2. **Verify sheet ID:**
   - Extract from Google Sheets URL
   - Ensure sheet is shared with your Google account

3. **Check sheet structure:**
   - Verify required columns exist
   - Check column names match expected format

4. **Test manually:**
   ```bash
   python sync_sheets.py --dry-run --verbose
   ```

### Tasks Not Importing

1. **Check validation:**
   - Ensure all required fields have values
   - Verify RunID is unique and not empty

2. **Check authority model:**
   - Tasks with status-only authority become shadow tasks
   - Full authority tasks are imported normally

3. **Check database:**
   ```bash
   fin sync-status --verbose
   ```

### Performance Issues

1. **Reduce sync frequency:**
   - Increase cron interval
   - Use random delays

2. **Limit concurrent syncs:**
   - Set `max_concurrent_syncs: 1` in config

3. **Monitor logs:**
   - Check for API rate limit errors
   - Look for slow database operations

## Development and Extension

### Adding New Remote Systems

1. **Create new sync strategy:**
   ```python
   class NewSystemSyncStrategy(BaseSyncStrategy):
       def sync_tasks(self, **kwargs):
           # Implementation here
           pass
   ```

2. **Add to factory:**
   ```python
   elif system_type == RemoteSystemType.NEW_SYSTEM:
       return NewSystemSyncStrategy(sync_engine)
   ```

3. **Update enums:**
   ```python
   class RemoteSystemType(Enum):
       NEW_SYSTEM = "new_system"
   ```

### Custom Task Mapping

Override the default mapping behavior:

```python
class CustomTaskMapper(TaskMapper):
    def _format_local_content(self, remote_task):
        # Custom formatting logic
        return f"Custom: {remote_task.content}"
```

## Support and Contributing

### Getting Help

1. Check the logs for detailed error messages
2. Verify configuration and environment variables
3. Test with `--dry-run` to see what would happen
4. Check the test suite for examples

### Contributing

1. Follow the existing code style
2. Add tests for new functionality
3. Update documentation
4. Ensure all tests pass

### Testing

Run the test suite:

```bash
# All tests
python -m pytest tests/ -v

# Specific test categories
python -m pytest tests/test_sync_engine.py -v
python -m pytest tests/test_sync_strategies.py -v
```

## Changelog

### Version 1.0.0
- Initial Google Sheets sync implementation
- Dual authority model support
- CLI integration
- Standalone sync scripts
- Multi-source configuration
- Cron automation support
- Comprehensive logging and error handling

## License

This functionality is part of fin-cli and follows the same license terms.

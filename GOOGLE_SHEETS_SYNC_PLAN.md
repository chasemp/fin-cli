# Google Sheets Connector Implementation Plan

## **Overview**
Create a modular system to pull tasks from Google Sheets into the local fin-cli task database, with proper synchronization, conflict resolution, and cron automation.

## **Architecture**
**Pull-based system** - no persistent services running. Sync happens on-demand via cron or user request, processes work, and exits cleanly.

## **Phase 1: Core Sheets Integration (Week 1)**
**Milestone 1.1: Enhanced Sheets Reader**
- Expand `gcreds.py` to read all rows from the specified sheet
- Parse the sheet structure: Source, RunID, Ts Time, User Name, Text, Permalink
- Add error handling and logging for API failures
- Create a `SheetsReader` class for reusable sheet operations

**Milestone 1.2: Task Mapping & Validation**
- Create task mapping logic: `"User Name" + Text + Permalink"`
- Add `#remote` tag to all imported tasks
- Validate required fields and handle missing data gracefully
- Create data models for sheet rows and task mappings

## **Phase 2: Database Integration & Sync Logic (Week 2)**
**Milestone 2.1: Remote Task Tracking**
- Add `remote_id` and `remote_source` fields to tasks table
- Create indexes for efficient remote task lookups
- Implement duplicate detection using RunID
- Add `last_synced_at` timestamp for sync tracking

**Milestone 2.2: Sync Engine**
- Implement one-by-one sync strategy (remove remote → add local → delete remote)
- Add transaction support to prevent partial sync failures
- Create sync status reporting and error handling
- Implement retry logic for failed operations

## **Phase 3: CLI Integration & Testing (Week 3)**
**Milestone 3.1: CLI Commands**
- Add `fin sync-sheets` command for manual sync
- Add `fin sync-status` to show sync status
- Integrate with existing `fin import` command structure
- Add dry-run mode for testing

**Milestone 3.2: Testing Framework**
- Create unit tests for sheets reader
- Create integration tests for sync logic
- Create mock Google Sheets API responses
- Test error scenarios and edge cases

## **Phase 4: Automation & Production (Week 4)**
**Milestone 4.1: Cron Script**
- Create standalone sync script (`sync_sheets.py`)
- Add configuration file support for multiple sheet sources
- Implement logging and monitoring
- Add health check endpoints

**Milestone 4.2: Production Deployment**
- Create installation and setup documentation
- Add environment variable configuration
- Create systemd service files for Linux
- Add monitoring and alerting

## **Technical Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Google Sheets │    │   Sync Engine    │    │   Local Tasks   │
│                 │◄──►│                  │◄──►│                 │
│ - Source        │    │ - SheetsReader   │    │ - Database      │
│ - RunID         │    │ - TaskMapper     │    │ - #remote tag   │
│ - User + Text   │    │ - SyncManager    │    │ - remote_id    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Cron Script    │
                       │                  │
                       │ - sync_sheets.py │
                       │ - Config files   │
                       │ - Logging        │
                       └──────────────────┘
```

## **Key Features**
1. **Safe Sync**: One-by-one processing prevents data loss
2. **Conflict Resolution**: Duplicate detection using RunID
3. **Audit Trail**: Track all sync operations and failures
4. **Configurable**: Support multiple sheet sources
5. **Resilient**: Retry logic and error handling
6. **Monitoring**: Logging and status reporting

## **Database Schema Changes**
```sql
-- Add to tasks table
ALTER TABLE tasks ADD COLUMN remote_id TEXT;
ALTER TABLE tasks ADD COLUMN remote_source TEXT;
ALTER TABLE tasks ADD COLUMN last_synced_at TIMESTAMP;

-- Create indexes
CREATE INDEX idx_tasks_remote_id ON tasks(remote_id);
CREATE INDEX idx_tasks_remote_source ON tasks(remote_source);
```

## **Configuration**
```bash
# Environment variables
GOOGLE_SHEET_ID=1TWob-vh6qZ1rzUNN1GMAxDl87UwH5P5ngyh2THeLcGo
GOOGLE_SYNC_INTERVAL=300  # 5 minutes
GOOGLE_SYNC_ENABLED=true
GOOGLE_SYNC_DRY_RUN=false
```

## **Testing Strategy**
1. **Unit Tests**: Mock Google Sheets API responses
2. **Integration Tests**: Test full sync workflow
3. **Error Tests**: Test API failures, network issues
4. **Performance Tests**: Test with large datasets
5. **End-to-End Tests**: Test complete cron workflow

## **Risk Mitigation**
- **Data Loss**: One-by-one sync with rollback capability
- **API Limits**: Rate limiting and exponential backoff
- **Network Issues**: Retry logic and offline mode
- **Schema Changes**: Backward compatibility and migration scripts

## **Success Criteria**
- ✅ Successfully sync tasks from Google Sheets
- ✅ Maintain data integrity during sync operations
- ✅ Handle errors gracefully with proper logging
- ✅ Support automated cron execution
- ✅ Comprehensive test coverage (>90%)
- ✅ Clear documentation and setup instructions

## **Implementation Status**
- [ ] Phase 1: Core Sheets Integration
- [ ] Phase 2: Database Integration & Sync Logic
- [ ] Phase 3: CLI Integration & Testing
- [ ] Phase 4: Automation & Production

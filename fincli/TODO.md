# FinCLI TODO

## Import Functionality Enhancements

### 🔥 High Priority

1. **Implement Google Sheets Integration**
   - [ ] Add `gspread` dependency to requirements.txt
   - [ ] Implement `import_sheets_tasks()` in `sheets_importer.py`
   - [ ] Add Google Sheets authentication (service account or OAuth)
   - [ ] Handle sheet formatting and data extraction
   - [ ] Add row deletion/marking after import
   - [ ] Test with real Google Sheets

2. **Implement Excel Integration**
   - [ ] Add `pandas` and `openpyxl` dependencies
   - [ ] Implement `import_excel_tasks()` in `excel_importer.py`
   - [ ] Handle multiple Excel formats (.xlsx, .xls)
   - [ ] Add sheet selection option
   - [ ] Test with real Excel files

### 🚀 Medium Priority

3. **Add Dry Run Functionality**
   - [ ] Implement dry-run mode in all importers
   - [ ] Show what would be imported without actually importing
   - [ ] Add `--dry-run` flag to CLI

4. **Add Logging**
   - [ ] Implement logging to `/tmp/fin-import.log`
   - [ ] Add log rotation
   - [ ] Include import timestamps and results

5. **Deduplication System**
   - [ ] Add hash-based deduplication
   - [ ] Store source_id for tracking
   - [ ] Prevent duplicate imports

### 📋 Low Priority

6. **Additional Import Sources**
   - [ ] Trello integration
   - [ ] GitHub Issues integration
   - [ ] Notion integration
   - [ ] Todoist integration

7. **Advanced Features**
   - [ ] Boolean logic for label filtering (AND/OR)
   - [ ] Multiple label support in import
   - [ ] Import scheduling with cron/launchd
   - [ ] Webhook support for real-time imports

### 🧪 Testing

8. **Comprehensive Testing**
   - [ ] Unit tests for all importers
   - [ ] Integration tests with sample files
   - [ ] Error handling tests
   - [ ] Performance tests for large imports

### 📚 Documentation

9. **Documentation Updates**
   - [ ] Update README with import examples
   - [ ] Add configuration examples
   - [ ] Create troubleshooting guide
   - [ ] Add API documentation

## Current Status

✅ **Completed:**
- Modular plugin architecture
- CSV importer (working)
- JSON importer (working)
- Text importer (working)
- CLI integration
- Error handling
- Source labeling

🔄 **In Progress:**
- Google Sheets integration (stub ready)

⏳ **Pending:**
- Excel integration
- Advanced features
- Additional sources 
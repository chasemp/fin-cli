# Fin Dashboard

A local-first, offline-capable task management dashboard that runs entirely in the browser using SQLite via WebAssembly.

## Features

- **🔒 Local-First**: All data stays on your device
- **📱 PWA**: Installable as a native app
- **⌨️ Keyboard-Centric**: Full keyboard navigation and shortcuts
- **🔍 Smart Filtering**: Search and filter by status, labels, dates
- **📊 SQLite Integration**: Direct database file loading/saving
- **🌙 Dark Mode**: Automatic dark mode support
- **📱 Responsive**: Works on desktop and mobile

## Quick Start

### Option 1: Quick Launch (Recommended)

```bash
# Open dashboard with default database (~/fin/tasks.db)
./open_dashboard.sh

# Open dashboard with specific database
./open_dashboard.sh ~/fin/tasks.db

# Or use the function (add to your shell profile)
source fin_dashboard.sh
fin ~/fin/tasks.db
```

### Option 2: Simple HTTP Server

```bash
# Navigate to the dashboard directory
cd fin-web/dashboard

# Start a simple HTTP server
python -m http.server 8000

# Open in browser
open http://localhost:8000
```

### Option 3: Direct File Access

```bash
# Open index.html directly in your browser
open index.html
```

## Usage

### Loading Your Database

**Automatic (when using scripts):**
- The dashboard will show the database path in the URL
- Click **"📁 Open DB"** to load the specified database
- The path will be displayed in the empty state

**Manual:**
1. Click **"📁 Open DB"** or press `Ctrl+S` to load your SQLite database
2. Select your `~/fin/tasks.db` file
3. Your tasks will appear grouped by date

### Adding Tasks

- **Click**: Floating "+" button
- **Keyboard**: Press `N` to open add task modal
- **Submit**: Press `Enter` or click "Save Task"
- **Cancel**: Press `Esc` or click "Cancel"
- **Labels**: Add comma-separated labels (e.g., "work, urgent")
- **Auto-save**: Changes are saved to browser storage automatically

### Managing Tasks

- **Toggle Completion**: Click checkbox or press `Space` on selected task
- **Search**: Press `/` to focus search, type to filter by content or labels
- **Status Filter**: Use "All", "Open", "Completed" buttons
- **Label Filters**: Click any label pill to filter by it (multi-select)
- **Clear Filters**: Press `Esc` to clear all filters

### Saving Changes

- **Auto-save**: Changes are automatically saved to browser storage
- **Export**: Click "💾 Save DB" to download updated database file
- **Sync**: Replace your `~/fin/tasks.db` with the downloaded file

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `N` | Add new task |
| `S` | Save database |
| `/` | Focus search |
| `↑/↓` | Navigate tasks |
| `Space` | Toggle task completion |
| `Esc` | Clear filters or close modals |
| `?` | Show help |
| `⌘⇧R` | Hard reload (clear cache) |

## File Structure

```
dashboard/
├── index.html          # Main HTML file
├── style.css           # Styling and responsive design
├── app.js              # Main application logic
├── manifest.json       # PWA manifest
├── serviceWorker.js    # Offline functionality
└── README.md          # This file
```

## Database Integration

The dashboard works with the same SQLite database used by the Fin CLI:

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    labels TEXT,
    source TEXT DEFAULT 'cli'
);
```

### Import Workflow

1. **CLI Import**: Use `fin-import` to import tasks from external sources
2. **Load in Dashboard**: Open the resulting `tasks.db` file
3. **Manage Tasks**: Use the web interface to organize and complete tasks
4. **Export**: Save the database and sync back to your system

## PWA Features

- **Installable**: Add to home screen on mobile/desktop
- **Offline**: Works without internet connection
- **Auto-update**: Service worker handles caching and updates

## Browser Compatibility

- **Chrome/Edge**: Full support
- **Firefox**: Full support
- **Safari**: Full support (iOS 11.3+)
- **Mobile**: Works on all modern mobile browsers

## Development

### Local Development

```bash
# Start development server
python -m http.server 8000

# Or use any other local server
npx serve .
```

### Customization

- **Styling**: Modify `style.css` for custom themes
- **Features**: Extend `app.js` for additional functionality
- **Database**: Modify SQL queries in `loadTasks()` method

## Troubleshooting

### Database Won't Load
- Ensure the file is a valid SQLite database
- Check that the database has the correct schema
- Try creating a new database with the CLI first

### PWA Not Installing
- Use HTTPS in production (required for PWA)
- Ensure manifest.json is accessible
- Check browser console for service worker errors

### Performance Issues
- Large databases (>1000 tasks) may be slow
- Consider filtering to recent tasks only
- Use browser dev tools to monitor memory usage

## Integration with Fin CLI

The dashboard is designed to work seamlessly with the Fin CLI:

```bash
# Import tasks from external sources
fin-import --source csv --file tasks.csv

# Load the database in the dashboard
# (Open dashboard and load the tasks.db file)

# Export changes back to your system
# (Save the database from dashboard and replace ~/fin/tasks.db)
```

## License

MIT License - see LICENSE file for details. 
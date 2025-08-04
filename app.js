// Fin Dashboard - Main Application
class FinDashboard {
    constructor() {
        this.db = null;
        this.tasks = [];
        this.filteredTasks = [];
        this.currentFilter = 'all';
        this.searchQuery = '';
        this.selectedTaskIndex = -1;
        this.isLoading = false;
        this.activeLabels = new Set(); // Track active label filters
        
        this.init();
    }
    
    async init() {
        // Wait for SQL.js to load
        if (typeof initSqlJs === 'undefined') {
            await this.loadSqlJs();
        }
        
        this.bindEvents();
        
        // Check for database path in URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        const dbPath = urlParams.get('db');
        
        if (dbPath) {
            // Show a helpful message about the database path
            this.showNotification(`Database path: ${dbPath} - Click "📁 Open DB" to load`, 'info');
            // Update the page title to show we have a database path
            document.title = `Fin Dashboard - ${dbPath}`;
            // Update empty state to show the database path
            const emptyState = document.getElementById('emptyState');
            if (emptyState) {
                emptyState.innerHTML = `
                    <p>No tasks found. Load database from:</p>
                    <p><code>${dbPath}</code></p>
                    <button id="addFirstTaskBtn" class="btn btn-primary">Add Task</button>
                `;
            }
        }
        
        // Always start with IndexedDB fallback
        this.loadFromIndexedDB();
    }
    
    async loadSqlJs() {
        return new Promise((resolve) => {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/sql-wasm.js';
            script.onload = () => {
                initSqlJs({ locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/${file}` })
                    .then(() => resolve());
            };
            document.head.appendChild(script);
        });
    }
    
    bindEvents() {
        // Button events
        document.getElementById('loadDbBtn').addEventListener('click', () => this.loadDatabase());
        document.getElementById('saveDbBtn').addEventListener('click', () => this.saveDatabase());
        document.getElementById('helpBtn').addEventListener('click', () => this.showHelp());
        document.getElementById('addTaskBtn').addEventListener('click', () => this.showAddTaskModal());
        document.getElementById('addFirstTaskBtn').addEventListener('click', () => this.showAddTaskModal());
        
        // Modal events
        document.getElementById('closeModalBtn').addEventListener('click', () => this.hideAddTaskModal());
        document.getElementById('closeHelpBtn').addEventListener('click', () => this.hideHelp());
        document.getElementById('cancelTaskBtn').addEventListener('click', () => this.hideAddTaskModal());
        document.getElementById('saveTaskBtn').addEventListener('click', () => this.saveTask());
        
        // Form submit for Enter key
        document.getElementById('addTaskForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveTask();
        });
        
        // Search and filter events
        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.searchQuery = e.target.value;
            this.filterTasks();
        });
        
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentFilter = e.target.dataset.filter;
                this.filterTasks();
            });
        });
        
        // File input
        document.getElementById('dbFileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.loadDatabaseFromFile(file);
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
        
        // Click outside modal to close
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.hideAddTaskModal();
                this.hideHelp();
            }
        });
    }
    
    handleKeydown(e) {
        // Don't handle shortcuts when typing in inputs
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        switch (e.key) {
            case 'n':
            case 'N':
                e.preventDefault();
                this.showAddTaskModal();
                break;
            case 's':
            case 'S':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    this.saveDatabase();
                }
                break;
            case '/':
                e.preventDefault();
                document.getElementById('searchInput').focus();
                break;
            case '?':
                e.preventDefault();
                this.showHelp();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.navigateTasks(-1);
                break;
            case 'ArrowDown':
                e.preventDefault();
                this.navigateTasks(1);
                break;
            case ' ':
                e.preventDefault();
                this.toggleSelectedTask();
                break;
            case 'Escape':
                this.hideAddTaskModal();
                this.hideHelp();
                // Clear all filters if no modals are open
                if (!document.querySelector('.modal:not(.hidden)')) {
                    this.clearAllFilters();
                }
                break;
            case 'r':
            case 'R':
                if (e.metaKey && e.shiftKey) {
                    e.preventDefault();
                    this.hardReload();
                }
                break;
        }
    }
    
    navigateTasks(direction) {
        if (this.filteredTasks.length === 0) return;
        
        this.selectedTaskIndex += direction;
        
        if (this.selectedTaskIndex < 0) {
            this.selectedTaskIndex = this.filteredTasks.length - 1;
        } else if (this.selectedTaskIndex >= this.filteredTasks.length) {
            this.selectedTaskIndex = 0;
        }
        
        this.updateTaskSelection();
    }
    
    updateTaskSelection() {
        // Remove previous selection
        document.querySelectorAll('.task-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Add selection to current task
        if (this.selectedTaskIndex >= 0 && this.selectedTaskIndex < this.filteredTasks.length) {
            const taskElements = document.querySelectorAll('.task-item');
            if (taskElements[this.selectedTaskIndex]) {
                taskElements[this.selectedTaskIndex].classList.add('selected');
                taskElements[this.selectedTaskIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    }
    
    toggleSelectedTask() {
        if (this.selectedTaskIndex >= 0 && this.selectedTaskIndex < this.filteredTasks.length) {
            const task = this.filteredTasks[this.selectedTaskIndex];
            this.toggleTaskCompletion(task.id);
        }
    }
    
    async loadDatabase() {
        document.getElementById('dbFileInput').click();
    }
    
    async loadDatabaseFromFile(file) {
        try {
            this.setLoading(true);
            
            const arrayBuffer = await file.arrayBuffer();
            this.db = new SQL.Database(new Uint8Array(arrayBuffer));
            
            // Create tasks table if it doesn't exist
            this.db.run(`
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    labels TEXT,
                    source TEXT DEFAULT 'cli'
                )
            `);
            
            await this.loadTasks();
            this.saveToIndexedDB();
            
            this.showNotification('Database loaded successfully!', 'success');
        } catch (error) {
            console.error('Error loading database:', error);
            this.showNotification('Error loading database. Please check the file format.', 'error');
        } finally {
            this.setLoading(false);
        }
    }
    

    
    async saveDatabase() {
        if (!this.db) {
            this.showNotification('No database loaded to save.', 'error');
            return;
        }
        
        try {
            this.setLoading(true);
            
            const data = this.db.export();
            const blob = new Blob([data], { type: 'application/x-sqlite3' });
            
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'tasks.db';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            this.showNotification('Database saved successfully!', 'success');
        } catch (error) {
            console.error('Error saving database:', error);
            this.showNotification('Error saving database.', 'error');
        } finally {
            this.setLoading(false);
        }
    }
    
    async loadTasks() {
        if (!this.db) return;
        
        try {
            // Get tasks from the last 7 days by default
            const sevenDaysAgo = new Date();
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
            const sevenDaysAgoStr = sevenDaysAgo.toISOString().split('T')[0];
            
            const result = this.db.exec(`
                SELECT id, content, created_at, completed_at, labels, source
                FROM tasks
                WHERE created_at >= '${sevenDaysAgoStr}'
                ORDER BY created_at DESC
            `);
            
            this.tasks = result[0] ? result[0].values.map(row => ({
                id: row[0],
                content: row[1],
                created_at: row[2],
                completed_at: row[3],
                labels: row[4] ? row[4].split(',') : [],
                source: row[5]
            })) : [];
            
            this.filterTasks();
        } catch (error) {
            console.error('Error loading tasks:', error);
        }
    }
    
    filterTasks() {
        this.filteredTasks = this.tasks.filter(task => {
            // Filter by status
            if (this.currentFilter === 'open' && task.completed_at) return false;
            if (this.currentFilter === 'completed' && !task.completed_at) return false;
            
            // Filter by search query
            if (this.searchQuery) {
                const query = this.searchQuery.toLowerCase();
                const contentMatch = task.content.toLowerCase().includes(query);
                const labelMatch = task.labels.some(label => label.toLowerCase().includes(query));
                if (!contentMatch && !labelMatch) return false;
            }
            
            // Filter by active labels
            if (this.activeLabels.size > 0) {
                const taskLabels = new Set(task.labels.map(label => label.toLowerCase()));
                const hasMatchingLabel = Array.from(this.activeLabels).some(activeLabel => 
                    taskLabels.has(activeLabel.toLowerCase())
                );
                if (!hasMatchingLabel) return false;
            }
            
            return true;
        });
        
        this.renderTasks();
        this.renderLabelFilters();
        this.renderActiveFilters();
    }
    
    renderTasks() {
        const taskList = document.getElementById('taskList');
        const emptyState = document.getElementById('emptyState');
        
        if (this.filteredTasks.length === 0) {
            taskList.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        
        // Group tasks by date
        const groups = this.groupTasksByDate(this.filteredTasks);
        
        let html = '';
        
        for (const [dateLabel, tasks] of Object.entries(groups)) {
            const openTasks = tasks.filter(t => !t.completed_at);
            const completedTasks = tasks.filter(t => t.completed_at);
            
            html += `
                <div class="task-group">
                    <div class="task-group-header ${completedTasks.length > 0 ? 'collapsed' : ''}" 
                         onclick="dashboard.toggleGroup(this)">
                        <span>${dateLabel}</span>
                        <span class="task-count">${tasks.length} tasks</span>
                    </div>
                    <div class="task-group-content">
            `;
            
            // Render open tasks
            openTasks.forEach(task => {
                html += this.renderTask(task);
            });
            
            // Render completed tasks (collapsed by default)
            if (completedTasks.length > 0) {
                html += `<div class="completed-tasks" style="display: none;">`;
                completedTasks.forEach(task => {
                    html += this.renderTask(task);
                });
                html += `</div>`;
            }
            
            html += `
                    </div>
                </div>
            `;
        }
        
        taskList.innerHTML = html;
        
        // Bind task events
        this.bindTaskEvents();
    }
    
    renderTask(task) {
        const isCompleted = !!task.completed_at;
        const timestamp = isCompleted ? task.completed_at : task.created_at;
        const formattedTime = new Date(timestamp).toLocaleString('en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const labelsHtml = task.labels.map(label => 
            `<span class="task-label" onclick="dashboard.filterByLabel('${label}')">${label}</span>`
        ).join('');
        
        return `
            <div class="task-item" data-task-id="${task.id}" tabindex="0">
                <div class="task-checkbox ${isCompleted ? 'checked' : ''}" 
                     onclick="dashboard.toggleTaskCompletion(${task.id})">
                    ${isCompleted ? '✓' : ''}
                </div>
                <div class="task-content">
                    <div class="task-text ${isCompleted ? 'completed' : ''}">${this.escapeHtml(task.content)}</div>
                    <div class="task-meta">
                        <span class="task-timestamp">${formattedTime}</span>
                        <div class="task-labels">${labelsHtml}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    groupTasksByDate(tasks) {
        const groups = {};
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        tasks.forEach(task => {
            const taskDate = new Date(task.created_at);
            let dateLabel;
            
            if (taskDate.toDateString() === today.toDateString()) {
                dateLabel = 'Today';
            } else if (taskDate.toDateString() === yesterday.toDateString()) {
                dateLabel = 'Yesterday';
            } else {
                dateLabel = 'Earlier This Week';
            }
            
            if (!groups[dateLabel]) {
                groups[dateLabel] = [];
            }
            groups[dateLabel].push(task);
        });
        
        return groups;
    }
    
    bindTaskEvents() {
        document.querySelectorAll('.task-item').forEach((item, index) => {
            item.addEventListener('click', () => {
                this.selectedTaskIndex = index;
                this.updateTaskSelection();
            });
            
            item.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const taskId = parseInt(item.dataset.taskId);
                    this.toggleTaskCompletion(taskId);
                }
            });
        });
    }
    
    toggleGroup(header) {
        const content = header.nextElementSibling;
        const completedTasks = content.querySelector('.completed-tasks');
        
        if (completedTasks) {
            const isHidden = completedTasks.style.display === 'none';
            completedTasks.style.display = isHidden ? 'block' : 'none';
            header.classList.toggle('collapsed', !isHidden);
        }
    }
    
    async toggleTaskCompletion(taskId) {
        if (!this.db) return;
        
        try {
            const task = this.tasks.find(t => t.id === taskId);
            if (!task) return;
            
            const isCompleted = !!task.completed_at;
            const newStatus = isCompleted ? 'NULL' : 'CURRENT_TIMESTAMP';
            
            this.db.run(`
                UPDATE tasks 
                SET completed_at = ${newStatus} 
                WHERE id = ?
            `, [taskId]);
            
            // Update local task
            task.completed_at = isCompleted ? null : new Date().toISOString();
            
            this.filterTasks();
            this.saveToIndexedDB();
            
            // Add completion animation
            const taskElement = document.querySelector(`[data-task-id="${taskId}"]`);
            if (taskElement) {
                taskElement.classList.add('completing');
                setTimeout(() => taskElement.classList.remove('completing'), 300);
            }
        } catch (error) {
            console.error('Error toggling task completion:', error);
            this.showNotification('Error updating task.', 'error');
        }
    }
    
    filterByLabel(label) {
        document.getElementById('searchInput').value = label;
        this.searchQuery = label;
        this.filterTasks();
    }
    
    showAddTaskModal() {
        document.getElementById('addTaskModal').classList.remove('hidden');
        document.getElementById('taskContent').focus();
    }
    
    hideAddTaskModal() {
        document.getElementById('addTaskModal').classList.add('hidden');
        document.getElementById('taskContent').value = '';
        document.getElementById('taskLabels').value = '';
    }
    
    showHelp() {
        document.getElementById('helpModal').classList.remove('hidden');
    }
    
    hideHelp() {
        document.getElementById('helpModal').classList.add('hidden');
    }
    
    async saveTask() {
        const content = document.getElementById('taskContent').value.trim();
        const labels = document.getElementById('taskLabels').value.trim();
        
        if (!content) {
            this.showNotification('Please enter a task description.', 'error');
            return;
        }
        
        // Show loading state
        const saveBtn = document.getElementById('saveTaskBtn');
        const originalText = saveBtn.textContent;
        saveBtn.textContent = 'Saving...';
        saveBtn.disabled = true;
        
        if (!this.db) {
            // Create a new database if none exists
            this.db = new SQL.Database();
            this.db.run(`
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    labels TEXT,
                    source TEXT DEFAULT 'web'
                )
            `);
        }
        
        try {
            const labelsArray = labels ? labels.split(',').map(l => l.trim()).filter(l => l) : [];
            const labelsStr = labelsArray.join(',');
            
            this.db.run(`
                INSERT INTO tasks (content, labels, source)
                VALUES (?, ?, 'web')
            `, [content, labelsStr]);
            
            await this.loadTasks();
            this.saveToIndexedDB();
            this.hideAddTaskModal();
            
            this.showNotification('Task added successfully!', 'success');
        } catch (error) {
            console.error('Error saving task:', error);
            this.showNotification('Error saving task.', 'error');
        } finally {
            // Restore button state
            saveBtn.textContent = originalText;
            saveBtn.disabled = false;
        }
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        document.body.classList.toggle('loading', loading);
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            color: white;
            font-weight: 500;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        if (type === 'success') {
            notification.style.backgroundColor = '#10b981';
        } else if (type === 'error') {
            notification.style.backgroundColor = '#ef4444';
        } else {
            notification.style.backgroundColor = '#3b82f6';
        }
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
    
    // IndexedDB for persistence
    async saveToIndexedDB() {
        if (!this.db) return;
        
        try {
            const data = this.db.export();
            localStorage.setItem('fin-dashboard-db', JSON.stringify(Array.from(data)));
        } catch (error) {
            console.error('Error saving to IndexedDB:', error);
        }
    }
    
    async loadFromIndexedDB() {
        try {
            const savedData = localStorage.getItem('fin-dashboard-db');
            if (savedData) {
                const data = new Uint8Array(JSON.parse(savedData));
                this.db = new SQL.Database(data);
                await this.loadTasks();
            }
        } catch (error) {
            console.error('Error loading from IndexedDB:', error);
        }
    }
    
    hardReload() {
        // Show notification
        this.showNotification('🔄 Hard reloading... Clearing all cache and reloading fresh', 'info');
        
        // Clear all cached state
        this.clearAllCache();
        
        // Reload the page with cache bypass
        setTimeout(() => {
            window.location.reload(true);
        }, 500);
    }
    
    clearAllCache() {
        // Clear localStorage
        localStorage.clear();
        
        // Clear IndexedDB if available
        if ('indexedDB' in window) {
            indexedDB.databases().then(databases => {
                databases.forEach(db => {
                    if (db.name.includes('fin') || db.name.includes('dashboard')) {
                        indexedDB.deleteDatabase(db.name);
                    }
                });
            });
        }
        
        // Clear service worker cache
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.getRegistrations().then(registrations => {
                registrations.forEach(registration => {
                    registration.unregister();
                });
            });
        }
        
        // Clear any in-memory state
        this.db = null;
        this.tasks = [];
        this.filteredTasks = [];
        this.currentFilter = 'all';
        this.searchQuery = '';
        this.selectedTaskIndex = -1;
        
        console.log('🧹 All cache cleared for hard reload');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    renderLabelFilters() {
        const labelFiltersContainer = document.getElementById('labelFilters');
        if (!labelFiltersContainer) return;
        
        // Get all unique labels from tasks
        const allLabels = new Set();
        this.tasks.forEach(task => {
            task.labels.forEach(label => {
                allLabels.add(label.toLowerCase());
            });
        });
        
        if (allLabels.size === 0) {
            labelFiltersContainer.innerHTML = '<p style="color: #6b7280; font-size: 0.875rem;">No labels found</p>';
            return;
        }
        
        const sortedLabels = Array.from(allLabels).sort();
        const html = sortedLabels.map(label => {
            const isActive = this.activeLabels.has(label);
            return `<button class="label-pill ${isActive ? 'active' : ''}" data-label="${this.escapeHtml(label)}">#${this.escapeHtml(label)}</button>`;
        }).join('');
        
        labelFiltersContainer.innerHTML = html;
        
        // Bind click events
        labelFiltersContainer.querySelectorAll('.label-pill').forEach(pill => {
            pill.addEventListener('click', (e) => {
                const label = e.target.dataset.label;
                this.toggleLabelFilter(label);
            });
        });
    }
    
    toggleLabelFilter(label) {
        if (this.activeLabels.has(label)) {
            this.activeLabels.delete(label);
        } else {
            this.activeLabels.add(label);
        }
        this.filterTasks();
    }
    
    renderActiveFilters() {
        const activeFiltersContainer = document.getElementById('activeFilters');
        if (!activeFiltersContainer) return;
        
        const activeFilters = [];
        
        // Add status filter
        if (this.currentFilter !== 'all') {
            activeFilters.push(`Status: ${this.currentFilter}`);
        }
        
        // Add label filters
        if (this.activeLabels.size > 0) {
            const labelList = Array.from(this.activeLabels).map(label => `#${label}`).join(', ');
            activeFilters.push(`Labels: ${labelList}`);
        }
        
        // Add search filter
        if (this.searchQuery) {
            activeFilters.push(`Search: "${this.searchQuery}"`);
        }
        
        if (activeFilters.length === 0) {
            activeFiltersContainer.classList.remove('show');
            return;
        }
        
        activeFiltersContainer.classList.add('show');
        activeFiltersContainer.innerHTML = `
            <strong>Active filters:</strong> ${activeFilters.map(filter => 
                `<span class="filter-tag">${this.escapeHtml(filter)}</span>`
            ).join(' ')}
            <button class="btn btn-secondary" style="margin-left: 0.5rem; padding: 0.125rem 0.5rem; font-size: 0.75rem;" onclick="dashboard.clearAllFilters()">Clear All</button>
        `;
    }
    
    clearAllFilters() {
        this.searchQuery = '';
        this.currentFilter = 'all';
        this.activeLabels.clear();
        
        // Update UI
        document.getElementById('searchInput').value = '';
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector('[data-filter="all"]').classList.add('active');
        
        this.filterTasks();
    }
}

// Initialize the dashboard
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new FinDashboard();
    
    // Register service worker for PWA functionality
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/serviceWorker.js')
            .then(registration => {
                console.log('ServiceWorker registration successful');
            })
            .catch(error => {
                console.log('ServiceWorker registration failed:', error);
            });
    }
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style); 
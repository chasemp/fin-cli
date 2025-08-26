#!/bin/bash
# Setup script for Google Sheets sync cron jobs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
CRON_TEMP_FILE="/tmp/fin_cli_sync_cron"

echo -e "${BLUE}🚀 Google Sheets Sync Cron Setup${NC}"
echo "=================================="
echo ""

# Check if we're in the right directory
if [[ ! -f "$PROJECT_ROOT/sync_multiple_sheets.py" ]]; then
    echo -e "${RED}❌ Error: This script must be run from the fin-cli project root${NC}"
    echo "   Current directory: $PROJECT_ROOT"
    echo "   Expected files: sync_multiple_sheets.py, sync_config.yaml"
    exit 1
fi

# Check if configuration file exists
if [[ ! -f "$PROJECT_ROOT/sync_config.yaml" ]]; then
    echo -e "${YELLOW}⚠️  Warning: sync_config.yaml not found${NC}"
    echo "   You'll need to create this file before setting up cron jobs"
    echo "   See sync_config.yaml.example for a template"
    echo ""
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 not found${NC}"
    echo "   Please install Python 3.7+ and try again"
    exit 1
fi

# Check if required Python packages are available
echo -e "${BLUE}🔍 Checking Python dependencies...${NC}"
cd "$PROJECT_ROOT"

if ! python3 -c "import yaml" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Warning: PyYAML not found${NC}"
    echo "   Installing PyYAML..."
    pip3 install PyYAML
fi

# Test the sync script
echo -e "${BLUE}🧪 Testing sync script...${NC}"
if python3 sync_multiple_sheets.py --help >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Sync script is working${NC}"
else
    echo -e "${RED}❌ Error: Sync script test failed${NC}"
    echo "   Please check that all dependencies are installed"
    exit 1
fi

echo ""
echo -e "${BLUE}📋 Available cron job options:${NC}"
echo ""

# Function to create cron job
create_cron_job() {
    local interval="$1"
    local description="$2"
    local cron_expression="$3"
    
    echo -e "${YELLOW}$description${NC}"
    echo "   Cron expression: $cron_expression"
    echo "   Command: cd $PROJECT_ROOT && python3 sync_multiple_sheets.py"
    echo ""
}

# Show cron job options
create_cron_job "every_15_min" "Every 15 minutes" "*/15 * * * *"
create_cron_job "every_30_min" "Every 30 minutes" "*/30 * * * *"
create_cron_job "every_hour" "Every hour" "0 * * * *"
create_cron_job "every_2_hours" "Every 2 hours" "0 */2 * * *"
create_cron_job "every_6_hours" "Every 6 hours" "0 */6 * * *"
create_cron_job "daily" "Daily at 9 AM" "0 9 * * *"
create_cron_job "weekdays" "Weekdays at 9 AM" "0 9 * * 1-5"

echo ""
echo -e "${BLUE}🔧 Setting up cron job...${NC}"
echo ""

# Ask user for preference
read -p "Choose cron interval (1-7): " choice

case $choice in
    1) cron_expression="*/15 * * * *" && description="Every 15 minutes" ;;
    2) cron_expression="*/30 * * * *" && description="Every 30 minutes" ;;
    3) cron_expression="0 * * * *" && description="Every hour" ;;
    4) cron_expression="0 */2 * * *" && description="Every 2 hours" ;;
    5) cron_expression="0 */6 * * *" && description="Every 6 hours" ;;
    6) cron_expression="0 9 * * *" && description="Daily at 9 AM" ;;
    7) cron_expression="0 9 * * 1-5" && description="Weekdays at 9 AM" ;;
    *) echo -e "${RED}Invalid choice. Exiting.${NC}" && exit 1 ;;
esac

# Create the cron job entry
cron_job="$cron_expression cd $PROJECT_ROOT && python3 sync_multiple_sheets.py >> $PROJECT_ROOT/sync.log 2>&1"

echo ""
echo -e "${BLUE}📝 Creating cron job:${NC}"
echo "   $cron_job"
echo ""

# Ask for confirmation
read -p "Add this cron job? (y/N): " confirm

if [[ $confirm =~ ^[Yy]$ ]]; then
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "sync_multiple_sheets.py"; then
        echo -e "${YELLOW}⚠️  Warning: A sync cron job already exists${NC}"
        echo "   Current cron jobs:"
        crontab -l 2>/dev/null | grep "sync_multiple_sheets.py" || true
        echo ""
        read -p "Replace existing job? (y/N): " replace
        
        if [[ ! $replace =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Cron job setup cancelled${NC}"
            exit 0
        fi
        
        # Remove existing sync jobs
        (crontab -l 2>/dev/null | grep -v "sync_multiple_sheets.py") | crontab -
    fi
    
    # Add new cron job
    (crontab -l 2>/dev/null; echo "$cron_job") | crontab -
    
    echo -e "${GREEN}✅ Cron job added successfully!${NC}"
    echo ""
    echo -e "${BLUE}📋 Current cron jobs:${NC}"
    crontab -l 2>/dev/null | grep "sync_multiple_sheets.py" || echo "   No sync jobs found"
    
else
    echo -e "${YELLOW}Cron job setup cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}📚 Next steps:${NC}"
echo "1. Edit sync_config.yaml to configure your Google Sheets sources"
echo "2. Ensure your Google OAuth token is valid and accessible"
echo "3. Test the sync manually: python3 sync_multiple_sheets.py --dry-run"
echo "4. Monitor sync.log for sync results and errors"
echo ""
echo -e "${BLUE}🔍 Useful commands:${NC}"
echo "   View cron jobs: crontab -l"
echo "   Edit cron jobs: crontab -e"
echo "   Remove all sync jobs: crontab -l | grep -v 'sync_multiple_sheets.py' | crontab -"
echo "   View sync logs: tail -f $PROJECT_ROOT/sync.log"
echo ""

echo -e "${GREEN}🎉 Setup complete! Your Google Sheets will sync automatically.${NC}"

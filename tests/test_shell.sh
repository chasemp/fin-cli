#!/bin/bash
# Shell script tests for Fin CLI
# Run with: bash tests/test_shell.sh

# Don't exit on error, let us handle it

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_output="$3"
    
    echo -e "${YELLOW}Running: $test_name${NC}"
    
    # Run the test command
    local output
    output=$(eval "$test_command" 2>&1)
    local exit_code=$?
    
    # Check if output contains expected text (strip emoji for comparison)
    clean_output=$(echo "$output" | sed 's/✅ //')
    clean_expected=$(echo "$expected_output" | sed 's/✅ //')
    
    # For help command, use grep to check if text is contained
    if [[ "$test_name" == *"Help command"* ]]; then
        if echo "$output" | grep -q "$clean_expected"; then
            echo -e "${GREEN}✅ PASS: $test_name${NC}"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}❌ FAIL: $test_name${NC}"
            echo "Expected: $expected_output"
            echo "Got: $output"
            ((TESTS_FAILED++))
        fi
    else
        if [ "$clean_output" = "$clean_expected" ]; then
            echo -e "${GREEN}✅ PASS: $test_name${NC}"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}❌ FAIL: $test_name${NC}"
            echo "Expected: $expected_output"
            echo "Got: $output"
            ((TESTS_FAILED++))
        fi
    fi
}

# Function to run a test that should fail
run_test_fail() {
    local test_name="$1"
    local test_command="$2"
    local expected_error="$3"
    
    echo -e "${YELLOW}Running: $test_name${NC}"
    
    # Run the test command
    local output
    output=$(eval "$test_command" 2>&1)
    local exit_code=$?
    
    # Check if command failed and contains expected error
    if [ $exit_code -ne 0 ] && echo "$output" | grep -q "$expected_error"; then
        echo -e "${GREEN}✅ PASS: $test_name${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL: $test_name${NC}"
        echo "Expected error: $expected_error"
        echo "Got: $output (exit code: $exit_code)"
        ((TESTS_FAILED++))
    fi
}

# Function to check database contents
check_database() {
    local db_path="$1"
    local expected_count="$2"
    local expected_content="$3"
    
    local actual_count
    actual_count=$(sqlite3 "$db_path" "SELECT COUNT(*) FROM tasks;" 2>/dev/null || echo "0")
    
    if [ "$actual_count" -eq "$expected_count" ]; then
        echo -e "${GREEN}✅ Database check passed: $expected_count tasks${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ Database check failed: expected $expected_count, got $actual_count${NC}"
        ((TESTS_FAILED++))
    fi
    
    # Check specific content if provided
    if [ -n "$expected_content" ]; then
        local actual_content
        actual_content=$(sqlite3 "$db_path" "SELECT content FROM tasks ORDER BY id DESC LIMIT 1;" 2>/dev/null || echo "")
        
        if [ "$actual_content" = "$expected_content" ]; then
            echo -e "${GREEN}✅ Content check passed: $expected_content${NC}"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}❌ Content check failed: expected '$expected_content', got '$actual_content'${NC}"
            ((TESTS_FAILED++))
        fi
    fi
}

# Setup temporary database
TEMP_DB=$(mktemp)
export FIN_DB_PATH="$TEMP_DB"

# Function to run fin command with proper environment
run_fin() {
    FIN_DB_PATH="$TEMP_DB" python -m fincli.cli "$@" 2>/dev/null
}

echo "🧪 Starting shell tests for Fin CLI..."
echo "📁 Using temporary database: $TEMP_DB"

# Test 1: Basic task addition
run_test \
    "Basic task addition" \
    "run_fin 'Test task'" \
    "✅ Task added: \"Test task\""

check_database "$TEMP_DB" 1 "Test task"

# Test 2: Task with labels
run_test \
    "Task with labels" \
    "run_fin 'Task with labels' --label work --label urgent" \
    "✅ Task added: \"Task with labels\" [work, urgent]"

check_database "$TEMP_DB" 2

# Test 3: Task with special characters
run_test \
    "Task with special characters" \
    "run_fin 'Task with quotes: \"hello\" and special chars: @#$%'" \
    "✅ Task added: \"Task with quotes: \"hello\" and special chars: @#$%\""

check_database "$TEMP_DB" 3

# Test 4: Empty task
run_test \
    "Empty task" \
    "run_fin ''" \
    "✅ Task added: \"\""

check_database "$TEMP_DB" 4

# Test 5: Missing argument (should fail)
run_test_fail \
    "Missing argument" \
    "FIN_DB_PATH=\"$TEMP_DB\" python -m fincli.cli" \
    "Missing argument"

check_database "$TEMP_DB" 4  # Should still have 4 tasks

# Test 6: Help command
run_test \
    "Help command" \
    "run_fin --help" \
    "Fin - A lightweight task tracking system"

# Test 7: Multiple tasks in sequence
run_test \
    "Multiple tasks in sequence" \
    "run_fin 'First task' >/dev/null && run_fin 'Second task' >/dev/null && run_fin 'Third task'" \
    "✅ Task added: \"Third task\""

check_database "$TEMP_DB" 7

# Test 8: Label normalization
run_test \
    "Label normalization" \
    "run_fin 'Normalized labels' --label WORK --label Urgent --label '  test  '" \
    "✅ Task added: \"Normalized labels\" [work, urgent, test]"

check_database "$TEMP_DB" 8

# Test 9: Empty labels
run_test \
    "Empty labels" \
    "run_fin 'Task with empty labels' --label '' --label '  ' --label valid" \
    "✅ Task added: \"Task with empty labels\" [valid]"

check_database "$TEMP_DB" 9

# Test 10: Custom source
run_test \
    "Custom source" \
    "run_fin 'Task with custom source' --source test" \
    "✅ Task added: \"Task with custom source\""

check_database "$TEMP_DB" 10

# Cleanup
rm -f "$TEMP_DB"

# Print summary
echo ""
echo "📊 Test Summary:"
echo -e "${GREEN}✅ Tests passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Tests failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All shell tests passed!${NC}"
    exit 0
else
    echo -e "${RED}💥 Some shell tests failed!${NC}"
    exit 1
fi 
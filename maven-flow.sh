#!/bin/bash

##############################################################################
# Maven Flow Wrapper Script Template
#
# This script runs Maven Flow autonomous development using Claude Code CLI.
# It iterates through incomplete PRD stories and executes them.
#
# This file is a template. The flow command copies this to maven-flow.sh
# when running Maven Flow in a project directory.
#
##############################################################################

set -e

# Color codes
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
CYAN=$'\033[0;36m'
MAGENTA=$'\033[0;35m'
GRAY=$'\033[0;90m'
BOLD=$'\033[1m'
NC=$'\033[0m' # No Color

# Parse arguments
MAX_ITERATIONS=${1:-100}
SLEEP_SECONDS=${2:-2}

# Timing variables
SCRIPT_START_TIME=$(date +%s)
TOTAL_STORIES_COMPLETED=0
TOTAL_STORIES_FAILED=0

##############################################################################
# UI Helper Functions
##############################################################################

# Spinner animation
spinner() {
    local pid=$1
    local message="$2"
    local delay=0.1
    local spinstr='|/-\'
    local start_time=$(date +%s)

    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        local temp=${spinstr#?}
        printf "\r${CYAN}[${spinstr:0:1}]${NC} ${message} ${GRAY}(${elapsed}s)${NC}" 2>/dev/null || true
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
    done
    printf "\r${GREEN}[✓]${NC} ${message} ${GRAY}($(($(date +%s) - start_time))s)${NC}\n"
}

# Format duration
format_duration() {
    local seconds=$1
    if [ $seconds -lt 60 ]; then
        echo "${seconds}s"
    elif [ $seconds -lt 3600 ]; then
        echo "$((seconds / 60))m $((seconds % 60))s"
    else
        echo "$((seconds / 3600))h $((seconds % 3600 / 60))m"
    fi
}

# Print section header
print_header() {
    local title="$1"
    echo ""
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
    printf "${MAGENTA}║${NC}  ${BOLD}%-60s${NC} ${MAGENTA}║${NC}\n" "$title"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
}

# Print info line
print_info() {
    local label="$1"
    local value="$2"
    printf "  ${CYAN}%-20s${NC} ${GREEN}%s${NC}\n" "$label:" "$value"
}

# Print status update
print_status() {
    local status="$1"
    local message="$2"
    echo -e "  ${GRAY}→${NC} ${CYAN}$status${NC}: $message"
}

##############################################################################
# Git Operations
##############################################################################

# Count files changed
count_changed_files() {
    git diff --name-only HEAD 2>/dev/null | wc -l || echo "0"
}

# Get changed files list
get_changed_files() {
    git diff --name-only HEAD 2>/dev/null || echo ""
}

##############################################################################
# Auto-commit function for Maven Flow
##############################################################################

commit_story_changes() {
    local story_id="$1"
    local prd_file="$2"

    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_status "SKIP" "Not in git repository"
        return 0
    fi

    # Check if there are any changes to commit
    if git diff --quiet && git diff --cached --quiet 2>/dev/null; then
        print_status "SKIP" "No changes detected"
        return 0
    fi

    # Extract story title from PRD for commit message
    local story_title=$(jq -r ".userStories[] | select(.id == \"$story_id\") | .title" "$prd_file" 2>/dev/null)

    if [ -z "$story_title" ]; then
        story_title="Story implementation"
    fi

    # Create semantic commit message
    local commit_message="feat: $story_id - $story_title"

    print_status "COMMIT" "$commit_message"

    # Stage all changes
    git add -A 2>/dev/null || true

    # Commit with the generated message
    if git commit -m "$commit_message" 2>/dev/null; then
        local commit_hash=$(git rev-parse --short HEAD 2>/dev/null)
        print_status "SUCCESS" "Committed as ${GREEN}$commit_hash${NC}"

        # Show what changed
        local files_changed=$(count_changed_files)
        print_status "FILES" "$files_changed file(s) modified"
    else
        print_status "WARN" "Failed to commit changes"
        return 1
    fi
}

##############################################################################
# Story Session Summary
##############################################################################

print_story_summary() {
    local story_id="$1"
    local story_title="$2"
    local start_time=$3
    local end_time=$4
    local success=$5

    local duration=$((end_time - start_time))

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}                    Session Summary                            ${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ "$success" = "true" ]; then
        print_info "Story" "$story_id - $story_title"
        print_info "Status" "${GREEN}COMPLETED${NC}"
        print_info "Duration" "$(format_duration $duration)"

        # Show git info if available
        if git rev-parse --git-dir > /dev/null 2>&1; then
            local commit_hash=$(git rev-parse --short HEAD 2>/dev/null)
            local branch=$(git branch --show-current 2>/dev/null)
            print_info "Commit" "$commit_hash"
            print_info "Branch" "$branch"
        fi
    else
        print_info "Story" "$story_id"
        print_info "Status" "${RED}FAILED${NC}"
        print_info "Duration" "$(format_duration $duration)"
    fi

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

##############################################################################
# Main Program
##############################################################################

# Find docs directory
DOCS_DIR="docs"
if [ ! -d "docs" ] && [ -d "../docs" ]; then
    DOCS_DIR="../docs"
fi

print_header "Maven Flow - Autonomous Development"

echo ""
echo -e "${CYAN}Configuration${NC}"
print_info "Max Iterations" "$MAX_ITERATIONS"
print_info "Sleep Between" "${SLEEP_SECONDS}s"
print_info "Docs Directory" "$DOCS_DIR"
echo ""

# Validate Claude Code CLI is available
if ! command -v claude &> /dev/null; then
    echo -e "${RED}Claude Code CLI not found${NC}"
    echo ""
    echo "Please install Claude Code CLI first:"
    echo "  npm install -g @anthropic-ai/claude-code"
    echo ""
    exit 1
fi

claude_version=$(claude --version 2>/dev/null || echo 'unknown')
print_info "Claude Code" "$claude_version"
echo ""

ITERATION=0
COMPLETED_STORIES=()

# Main loop
while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Iteration ${BOLD}$ITERATION${NC}${BLUE} of $MAX_ITERATIONS${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Find next incomplete story
    NEXT_STORY=""
    NEXT_PRD=""
    NEXT_PRD_FILE=""
    NEXT_STORY_TITLE=""

    print_status "SCANNING" "Looking for incomplete stories..."

    for prd_file in "$DOCS_DIR"/prd-*.json; do
        if [ -f "$prd_file" ]; then
            story_id=$(jq -r '.userStories[] | select(.passes == false) | .id' "$prd_file" 2>/dev/null | head -1)

            if [ -n "$story_id" ]; then
                NEXT_STORY="$story_id"
                NEXT_PRD=$(jq -r '.project' "$prd_file" 2>/dev/null)
                NEXT_PRD_FILE="$prd_file"
                NEXT_STORY_TITLE=$(jq -r ".userStories[] | select(.id == \"$story_id\") | .title" "$prd_file" 2>/dev/null)
                break
            fi
        fi
    done

    if [ -z "$NEXT_STORY" ]; then
        echo ""
        echo -e "${GREEN}✓ All stories complete!${NC}"
        echo ""
        echo -e "${CYAN}Completed Stories:${NC}"
        for story in "${COMPLETED_STORIES[@]}"; do
            echo -e "  ${GREEN}•${NC} $story"
        done
        echo ""

        total_duration=$(($(date +%s) - SCRIPT_START_TIME))
        print_info "Total Runtime" "$(format_duration $total_duration)"
        print_info "Stories Completed" "${#COMPLETED_STORIES[@]}"

        echo ""
        print_header "Maven Flow Complete"
        exit 0
    fi

    print_info "Next Story" "${YELLOW}$NEXT_STORY${NC}"
    print_info "Title" "$NEXT_STORY_TITLE"
    print_info "PRD" "$NEXT_PRD"
    echo ""

    # Create the prompt for Claude
    PROMPT='You are the Maven Flow autonomous development system.

## Current Task

Implement story: $NEXT_STORY from PRD: $NEXT_PRD

## Maven Steps to Execute

Read $NEXT_PRD_FILE for full story details and acceptance criteria.

## Instructions

1. Read the PRD file to understand the story requirements
2. Execute the mavenSteps listed for this story
3. Wait for each step to complete before starting the next
4. If successful:
   - The Maven Flow wrapper will auto-commit your changes
   - Update the PRD file: Set passes: true for this story
5. If failed:
   - Do NOT mark story complete
   - Output what went wrong

## Critical Rules

- NO '\''any'\'' types in code
- NO gradients in CSS/UI (solid colors only)
- NO emojis in UI components
- Follow Apple design methodology for professional polish

## Autonomous Mode Constraints

- NEVER use AskUserQuestion tool - this is non-interactive autonomous mode
- Make reasonable decisions when multiple options exist
- Choose the simplest, most standard approach
- If you encounter an ambiguous situation:
  1. Choose the option that follows best practices
  2. Document your decision in comments
  3. Continue with implementation
- For missing values (API keys, config), use placeholder values and document

## Output Format

After completing the story, output: <promise>STORY_COMPLETE</promise>

Begin implementation now.'

    # Track story execution time
    STORY_START_TIME=$(date +%s)

    echo ""
    print_status "STARTING" "Claude Code agent session"
    echo ""

    # Run Claude Code with spinner
    claude --dangerously-skip-permissions -p "$PROMPT" &
    CLAUDE_PID=$!

    # Show spinner while Claude runs
    spinner $CLAUDE_PID "AI agent working"

    wait $CLAUDE_PID
    CLAUDE_EXIT_CODE=$?

    STORY_END_TIME=$(date +%s)

    echo ""

    # Check result
    if [ $CLAUDE_EXIT_CODE -eq 0 ]; then
        COMPLETED_STORIES+=("$NEXT_STORY")
        TOTAL_STORIES_COMPLETED=$((TOTAL_STORIES_COMPLETED + 1))

        print_status "SUCCESS" "Story $NEXT_STORY completed"
        echo ""

        # Auto-commit changes after successful story completion
        commit_story_changes "$NEXT_STORY" "$NEXT_PRD_FILE"

        # Print session summary
        print_story_summary "$NEXT_STORY" "$NEXT_STORY_TITLE" $STORY_START_TIME $STORY_END_TIME "true"

        # Sleep between iterations
        if [ $ITERATION -lt $MAX_ITERATIONS ]; then
            echo ""
            print_status "WAITING" "Pausing ${SLEEP_SECONDS}s before next iteration..."
            sleep $SLEEP_SECONDS
        fi
    else
        TOTAL_STORIES_FAILED=$((TOTAL_STORIES_FAILED + 1))

        print_status "ERROR" "Story $NEXT_STORY failed (exit code: $CLAUDE_EXIT_CODE)"
        echo ""

        # Print session summary
        print_story_summary "$NEXT_STORY" "$NEXT_STORY_TITLE" $STORY_START_TIME $STORY_END_TIME "false"

        echo ""
        print_status "CONTINUING" "Moving to next story..."
        sleep $SLEEP_SECONDS
    fi

    echo ""
done

# Max iterations reached
echo ""
total_duration=$(($(date +%s) - SCRIPT_START_TIME))
print_header "Maven Flow - Max Iterations Reached"

echo ""
print_info "Total Runtime" "$(format_duration $total_duration)"
print_info "Iterations Completed" "$ITERATION"
print_info "Stories Succeeded" "${GREEN}$TOTAL_STORIES_COMPLETED${NC}"
print_info "Stories Failed" "${RED}$TOTAL_STORIES_FAILED${NC}"
echo ""

if [ ${#COMPLETED_STORIES[@]} -gt 0 ]; then
    echo -e "${CYAN}Completed Stories:${NC}"
    for story in "${COMPLETED_STORIES[@]}"; do
        echo -e "  ${GREEN}•${NC} $story"
    done
    echo ""
fi

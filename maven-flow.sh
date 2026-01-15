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
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Parse arguments
MAX_ITERATIONS=${1:-100}
SLEEP_SECONDS=${2:-2}

# Find docs directory
DOCS_DIR="docs"
if [ ! -d "docs" ] && [ -d "../docs" ]; then
    DOCS_DIR="../docs"
fi

echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
echo -e "${MAGENTA}     Maven Flow Autonomous Development Starting${NC}"
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo -e "  Max Iterations: ${GREEN}$MAX_ITERATIONS${NC}"
echo -e "  Sleep Between: ${GREEN}${SLEEP_SECONDS}s${NC}"
echo -e "  Docs Directory: ${GREEN}${DOCS_DIR}${NC}"
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

echo -e "${GREEN}Claude Code CLI found$(claude --version 2>/dev/null || echo ' (version unknown)')${NC}"
echo ""

ITERATION=0
COMPLETED_STORIES=()

# Main loop
while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Iteration $ITERATION of $MAX_ITERATIONS${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Find next incomplete story
    NEXT_STORY=""
    NEXT_PRD=""
    NEXT_PRD_FILE=""

    for prd_file in "$DOCS_DIR"/prd-*.json; do
        if [ -f "$prd_file" ]; then
            story_id=$(jq -r '.userStories[] | select(.passes == false) | .id' "$prd_file" 2>/dev/null | head -1)

            if [ -n "$story_id" ]; then
                NEXT_STORY="$story_id"
                NEXT_PRD=$(jq -r '.project' "$prd_file" 2>/dev/null)
                NEXT_PRD_FILE="$prd_file"
                break
            fi
        fi
    done

    if [ -z "$NEXT_STORY" ]; then
        echo -e "${GREEN}All stories complete!${NC}"
        echo ""
        echo -e "${CYAN}Completed Stories:${NC}"
        for story in "${COMPLETED_STORIES[@]}"; do
            echo -e "  ${GREEN}*${NC} $story"
        done
        echo ""
        echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${MAGENTA}     Maven Flow Run Complete - All Stories Done${NC}"
        echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
        exit 0
    fi

    echo -e "${CYAN}Next Story:${NC} ${YELLOW}$NEXT_STORY${NC}"
    echo -e "${CYAN}PRD:${NC} $NEXT_PRD"
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
   - Commit changes with message: feat: [STORY_ID] - [Story Title]
   - Update the PRD file: Set passes: true for this story
5. If failed:
   - Do NOT commit
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

    echo -e "${YELLOW}Executing story with Claude Code...${NC}"
    echo ""

    # Run Claude Code with the prompt using -p flag to avoid stdin issues
    if claude --dangerously-skip-permissions -p "$PROMPT"; then
        COMPLETED_STORIES+=("$NEXT_STORY")
        echo ""
        echo -e "${GREEN}Story $NEXT_STORY completed${NC}"

        # Sleep between iterations
        if [ $ITERATION -lt $MAX_ITERATIONS ]; then
            echo ""
            echo -e "${CYAN}Sleeping ${SLEEP_SECONDS}s before next iteration...${NC}"
            sleep $SLEEP_SECONDS
        fi
    else
        echo ""
        echo -e "${RED}Story $NEXT_STORY failed${NC}"
        echo -e "${YELLOW}Continuing to next story...${NC}"
        sleep $SLEEP_SECONDS
    fi

    echo ""
done

echo ""
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
echo -e "${MAGENTA}     Maven Flow Run Complete - Max Iterations Reached${NC}"
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"

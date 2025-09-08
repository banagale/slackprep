# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SlackPrep is a Python CLI tool that converts Slack conversation exports into useful data for LLM contexts. It exports Slack conversations from a target date range or individual channels/conversations, then processes them into Markdown with proper conversational turns, image placeholders, and emoji conversion.

## Development Commands

### Environment Setup
```bash
# Install dependencies
poetry install

# Test installation
poetry run slackprep --help
```

### Code Quality
```bash
# Run linting and formatting
poetry run ruff check src/
poetry run ruff format src/

# Run tests
poetry run pytest
```

### Running the CLI
```bash
# Basic usage examples
poetry run slackprep --help
poetry run slackprep fetch-all --start-date 2025-06-01 --end-date 2025-07-07 --cleanup --prep
poetry run slackprep fetch C08ABCXYZ --prep
poetry run slackprep reassemble --input-dir data/input/some_export
```

## Architecture

The codebase consists of three main modules:

### CLI Module (`cli.py`)
- Main entry point with argument parsing and command dispatch
- Handles three primary commands: `fetch`, `fetch-all`, and `reassemble`
- Manages Slack token validation and authentication
- Coordinates between data fetching (via slackdump) and processing

### Reassemble Module (`reassemble.py`)
- Core message processing logic that converts raw Slack JSON into structured output
- Handles user lookup, timestamp formatting, link/mention normalization
- Converts Slack emoji syntax to Unicode emojis where possible
- Supports both Markdown and JSONL output formats
- Groups consecutive messages from the same user (turn grouping)
- Processes file attachments and creates proper markdown image/file references

### Cleanup Module (`cleanup_slackdump.py`)
- Removes unused files and directories from Slack exports
- Preserves only referenced uploads and essential metadata
- Can be run as standalone script or integrated into main workflow

### Data Flow
1. **Export**: Uses external `slackdump` tool to fetch Slack data via API
2. **Cleanup**: Removes unused files to reduce data size
3. **Reassemble**: Processes JSON messages into human-readable format with proper formatting

### File Structure
- `data/input/`: Raw Slack export data (JSON format)
- `data/output/`: Processed output files (Markdown/JSONL)
- `__uploads/`: Attached files from Slack conversations

## Dependencies

- **External**: Requires `slackdump` binary (Go tool) for Slack API interaction
- **Python**: Uses Poetry for dependency management with Python 3.12+
- **Key libraries**: requests (API calls), getpass4 (secure token input)
- **Dev tools**: ruff (linting/formatting), pytest (testing), pre-commit (hooks)

## Configuration

- Slack API token required (passed via `--token` or `SLACK_API_TOKEN` environment variable)
- Supports both user tokens (`xoxp-`) and bot tokens (`xoxb-`)
- Ruff configuration in pyproject.toml with 120-character line length and Python 3.12 target
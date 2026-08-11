# Claude Code guidance

Follow the canonical project instructions in `AGENTS.md`.

SlackPrep is a Python 3.12+ CLI with three primary modules:

- `src/slackprep/cli.py`: argument parsing, bounded Slackdump 4 exports, and workflow coordination.
- `src/slackprep/reassemble.py`: Markdown/JSONL transformation and filtering.
- `src/slackprep/cleanup_slackdump.py`: removal of unused export data and attachments.

Do not make live Slack requests during routine development or testing. Fetch commands require configured Slackdump 4
workspace authentication and explicit UTC time bounds; attachments remain opt-in.

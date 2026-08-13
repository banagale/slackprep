# Changelog

## v0.3.0 - 2026-08-13

- Build and install SlackPrep as a wheel or source distribution on Python 3.12 and newer.
- Document isolated installation with `uv tool install` and `pipx install`.
- Require bounded Slackdump 4 fetches with full UTC timestamps in `YYYY-MM-DDTHH:MM:SS` format.
- Use configured Slackdump workspaces for authentication and keep file downloads off unless `--files` is supplied.
- Document Contextify Total Recall as an optional way for Claude Code and Codex to retrieve prior AI-session context.

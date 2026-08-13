# SlackPrep

Turn Slackdump exports into Markdown or JSONL that is useful as LLM context. SlackPrep groups conversational turns,
resolves author names, renders attachment references, converts common Slack emoji, and can filter bot or automation
noise.

Current release: **v0.3.0**. SlackPrep requires Python 3.12 or newer.

## Install

Install SlackPrep's v0.3.0 wheel in an isolated environment with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install https://github.com/banagale/slackprep/releases/download/v0.3.0/slackprep-0.3.0-py3-none-any.whl
slackprep --help
```

Alternatively, use pipx:

```bash
pipx install https://github.com/banagale/slackprep/releases/download/v0.3.0/slackprep-0.3.0-py3-none-any.whl
slackprep --help
```

Converting an existing export needs only SlackPrep. Fetching from Slack also requires Slackdump 4. On macOS, install
Slackdump and configure an encrypted workspace through its browser-based authentication flow:

```bash
brew install slackdump
slackdump wiz
```

Slackdump stores workspace credentials outside this repository. SlackPrep uses configured Slackdump workspaces only;
it does not accept or persist Slack tokens.

## Export One Channel or DM

Every SlackPrep fetch requires a bounded interval with full UTC timestamps in `YYYY-MM-DDTHH:MM:SS` format.
Attachments are not downloaded unless `--files` is present, and Slackdump is instructed to enumerate only users
involved in the selected conversations.

```bash
slackprep fetch C08ABCXYZ \
  --time-from 2026-07-13T15:09:00 \
  --time-to   2026-07-13T17:54:00 \
  --api-config /path/to/conservative-api.toml \
  --prep
```

Get a channel or DM ID by copying its Slack link. Use `--files` only when attachment bodies are required.

## Export All Accessible Conversations

`fetch-all` is intentionally bounded but can still make many API requests. Prefer `fetch` for routine work and keep
the UTC interval narrow.

```bash
slackprep fetch-all \
  --time-from 2026-07-13T00:00:00 \
  --time-to   2026-07-14T00:00:00 \
  --api-config /path/to/conservative-api.toml \
  --cleanup \
  --prep
```

Add `--human-only` to apply all bot and automation filters during `--prep`.

## Convert an Existing Export

```bash
unzip slack-export.zip -d data/input/my_export
slackprep reassemble --input-dir data/input/my_export
```

Choose JSONL or filtering options as needed:

```bash
slackprep reassemble --input-dir data/input/my_export --format jsonl
slackprep reassemble --input-dir data/input/my_export --filter-bots
slackprep reassemble --input-dir data/input/my_export --filter-automation-channels
slackprep reassemble --input-dir data/input/my_export --filter-automated-content
slackprep reassemble --input-dir data/input/my_export --human-only
```

Raw exports are written under `data/input/`; processed output is written under `data/output/`. Keep private exports
and credentials out of Git.

## Run Slackdump Directly

For controls beyond the SlackPrep wrapper, use the configured Slackdump workspace and preserve the same safety
defaults:

```bash
slackdump export \
  -time-from 2026-07-13T15:09:00 \
  -time-to   2026-07-13T17:54:00 \
  -files=false \
  -channel-users \
  -api-config /path/to/conservative-api.toml \
  -o data/input/bounded_export \
  C08ABCXYZ
```

## Development and Testing

Clone the repository and install its development dependencies with Poetry (run through `uvx`, so a global Poetry
installation is not required):

```bash
git clone git@github.com:banagale/slackprep.git
cd slackprep
uvx --from poetry poetry install --with dev
uvx --from poetry poetry run pytest -q
uvx --from poetry poetry run ruff check src tests
uvx --from poetry poetry run ruff format --check src tests
uvx --from poetry poetry run slackprep --help
```

An existing private export can be used for an opt-in integration check:

```bash
SLACKPREP_LIVE_EXPORT=/path/to/local/export \
  uvx --from poetry poetry run pytest -q -m integration
```

The integration test reads local files only and never calls Slack. See `AGENTS.md` for the complete maintenance and
Slack safety rules.

## Related: Searchable AI Session History

SlackPrep prepares selected Slack conversations for LLM context. If you also want Claude Code or Codex to retrieve
decisions, code patterns, and solutions from indexed past AI sessions, see [Contextify Total Recall](https://contextify.sh/).

## Release Notes

See the [changelog](https://github.com/banagale/slackprep/blob/main/CHANGELOG.md) for release history.

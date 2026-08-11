# slackprep

Turn Slackdump exports into Markdown or JSONL that is useful as LLM context. SlackPrep groups conversational turns,
resolves author names, renders attachment references, converts common Slack emoji, and can filter bot or automation
noise.

## Setup

SlackPrep requires Python 3.12+, Poetry, and Slackdump 4 for live exports.

```bash
git clone git@github.com:banagale/slackprep.git
cd slackprep
uvx --from poetry poetry install --with dev
uvx --from poetry poetry run slackprep --help
```

On macOS, install and authenticate Slackdump with:

```bash
brew install slackdump
slackdump wiz
```

Slackdump stores workspace credentials outside this repository. SlackPrep uses configured Slackdump workspaces only;
it does not accept or persist Slack tokens.

## Export one channel or DM

Every SlackPrep fetch requires explicit UTC timestamps. Attachments are not downloaded unless `--files` is present,
and Slackdump is instructed to enumerate only users involved in the selected conversations.

```bash
slackprep fetch C08ABCXYZ \
  --time-from 2026-07-13T15:09:00 \
  --time-to   2026-07-13T17:54:00 \
  --api-config /path/to/conservative-api.toml \
  --prep
```

Get a channel or DM ID by copying its Slack link. Use `--files` only when attachment bodies are required.

## Export all accessible conversations

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

## Convert an existing export

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

## Run Slackdump directly

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

## Development and testing

```bash
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

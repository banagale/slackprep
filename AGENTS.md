# SlackPrep agent guidance

## Project overview

SlackPrep is a Python 3.12+ CLI that converts Slackdump 4 exports to Markdown and JSONL. The primary modules are
`src/slackprep/cli.py`, `src/slackprep/reassemble.py`, and `src/slackprep/cleanup_slackdump.py`.

Slackdump 4 is an external runtime dependency. On macOS, install it with `brew install slackdump` and configure an
encrypted workspace with `slackdump wiz` before using a fetch command.

## Standard commands

Poetry may not be installed globally. Use `uvx` as the supported fallback:

```bash
uvx --from poetry poetry install --with dev
uvx --from poetry poetry run pytest -q
uvx --from poetry poetry run ruff check src tests
uvx --from poetry poetry run ruff format --check src tests
uvx --from poetry poetry run slackprep --help
```

## Mandatory validation

- Run the sanitized offline test suite for every behavioral change.
- Run a Python 3.12 check for dependency or packaging changes.
- Use `SLACKPREP_LIVE_EXPORT` only with a pre-existing local export.
- Never make Slack network calls from normal pytest or CI.

## Slack safety

- Never perform broad or unbounded exports for validation.
- Constrain every export to an explicit conversation where possible and an explicit UTC time range.
- Keep file downloads disabled unless they are specifically required.
- Use `-channel-users` and a conservative Slackdump API configuration.
- Never place tokens or private Slack exports in Git or print private message text during structural validation.
- Inspect staged files before committing. `data/` is ignored, but other generated paths may not be.

Run the opt-in, local-only integration test with:

```bash
SLACKPREP_LIVE_EXPORT=/path/to/local/export \
  uvx --from poetry poetry run pytest -q -m integration
```

## Commit attribution

- Author and committer: `Rob Banagale <rob@banagale.com>`.
- Do not add AI co-author trailers or generated-by footers.

## Task management

This repository is not registered with Bloon. Do not assume a Bloon task exists or create `project-config.yaml` as
part of unrelated maintenance.

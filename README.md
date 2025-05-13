# slackprep

**slackprep** is a CLI tool and Python library that converts Slack export data into structured Markdown or JSONL transcripts. It supports workflows for summarization, prompt engineering, embedding, and file-aware developer tools like FileKitty.

---

## Features

- Groups or flattens speaker turns
- Resolves user IDs via `users.json`
- Converts Slack-formatted links, mentions, emoji, and code blocks
- Renders image attachments and links to other files
- Outputs Markdown (for prompts) or JSONL (for embedding)
- Copies only referenced files from `__uploads/`
- Writes per-conversation output folders under `data/output/`
- Adds symlink to original input folder (macOS only)

---

## Expected Input Format

slackprep operates on Slack export folders containing:

- `users.json`
- One or more subfolders (e.g. `mpdm-*`, `C08*`, `D0*`) with `.json` messages
- An optional `__uploads/` folder containing files

We recommend using [`slackdump`](https://github.com/rusq/slackdump) to generate compatible exports:

```shell
brew install slackdump # or whatever is appropriate on your system
```

---

## Getting a Slack Conversation ID

Right-click a Slack channel or DM > **Copy link**. Extract the ID from the URL:

`https://workspace.slack.com/archives/C08CSAH829K` → `C08CSAH829K`

---

## Usage

### Export Slack data

```bash
slackdump export -o data/input/slackdump_C08CSAH829K_$(date +%Y%m%d_%H%M%S) C08CSAH829K
````

Or use the `slackprep fetch` wrapper:

```bash
poetry run slackprep fetch C08CSAH829K
```

To export and immediately convert:

```bash
poetry run slackprep fetch --prep C08CSAH829K
```

### Convert to Markdown or JSONL

```bash
poetry run slackprep reassemble slackdump_C08CSAH829K_20250513_091057
```

Note: You can use partial folder name here, i.e. 091 will match the above.

---

## CLI Reference

```bash
poetry run slackprep <command> [options]
```

### fetch \<channel\_id>

Fetch Slack messages using `slackdump`.

Options:

* `--prep` — run `reassemble` immediately after export

### reassemble \[\<folder\_token>]

Convert a Slack export to Markdown or JSONL.

Options:

* `--input-dir <path>` — override folder auto-detection
* `--output <file>` — specify output file path
* `--format markdown|jsonl` — chose output format (default: markdown)
* `--all-turns` — do not group speaker turns
* `--absolute-timestamps` — include full timestamp
* `--use-symlink-for-attachments` — symlink uploads instead of copying

---

## Output Layout

```
data/output/slackdump_C08CSAH829K_20250513_091057/
├── reassembled_grouped_2025-05-13T09-31.md
├── __uploads/
└── original_input → ../../input/slackdump_C08CSAH829K_20250513_091057
```

---

## Development

```bash
poetry install
poetry run pytest
poetry run ruff check .
poetry run ruff format .
```

---

## License

MIT

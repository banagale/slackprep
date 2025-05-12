# slackprep

**slackprep** is a command-line utility and Python library that converts raw Slack export data into clean, structured,
LLM-friendly Markdown transcripts. It supports workflows for embedding, summarization, RAG augmentation, and developer
context tools like FileKitty.

---

## ✨ Features

- Groups Slack DM/MPDM conversation threads across multiple days
- Resolves user IDs to real names using `users.json`
- Groups consecutive messages by speaker with blank lines for readability
- Detects and renders:
    - Slack-formatted links (`<url|label>`) as Markdown
    - Mentions (`<@UXXXXXX>`) as `@Full Name`
    - Common emoji shortcodes (e.g. `:rolling_on_the_floor_laughing:` → 🤣)
    - Code blocks with triple-backtick fencing
    - Archive and image attachments using relative paths
- Outputs Markdown suitable for prompt injection or retrieval

---

## 📦 Usage

From inside a Slack export directory:

```bash
cd data/slackdumps/2025-05-12-dump
poetry run slackprep
````

### CLI Options

```bash
poetry run slackprep [options]
```

Available flags:

* `--all-turns` — do not group consecutive messages by speaker
* `--absolute-timestamps` — include full timestamps instead of just dates

---

## 📁 Directory Layout

```
slackprep/
├── pyproject.toml
├── README.md
├── .gitignore
├── data/
│   └── slackdumps/
│       └── 2025-05-12-dump/
│           ├── users.json
│           ├── mpdm-rob--eric--vlad/
│           └── __uploads/
└── src/
    └── slackprep/
        └── reassemble.py
```

---

## 🧪 Development

Install dependencies:

```bash
poetry install
```

Run tests:

```bash
poetry run pytest
```

Lint and format:

```bash
poetry run ruff check .
poetry run ruff format .
```

---

## 🔮 Roadmap

* `--output` path support
* Optional `.jsonl` format for embedding pipelines
* Thread/topic summarization scaffolding
* Integration with FileKitty for side-by-side context injection

---

## 🛡️ License

MIT

---

## 👤 Author

Rob Banagale

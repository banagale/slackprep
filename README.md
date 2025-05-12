# slackprep

**slackprep** is a command-line utility and library for converting raw Slack exports into clean, structured, LLM-friendly transcripts. It is designed to support workflows that bring Slack conversations into large language models for context-aware analysis, retrieval, or enrichment.

---

## ✨ Features

- Reassembles Slack DM or MPDM conversation threads across multiple days
- Resolves user IDs into real names using `users.json`
- Converts message threads into Markdown format with:
  - Speaker labels and timestamps
  - Slack-formatted links rendered as Markdown links
  - Uploaded images annotated with vision-aware notes
- Output is optimized for prompt injection or RAG pipelines

---

## 📦 Usage

```bash
python reassemble_conversations.py
````

This will:

* Walk all DM/MPDM directories in the Slack export folder
* Reconstruct messages in chronological order
* Output a `reassembled_conversation.md` file in the project root

---

## 🧪 Development

Set up with [Poetry](https://python-poetry.org/):

```bash
poetry install
```

Run tests with:

```bash
poetry run pytest
```

Lint and autoformat:

```bash
poetry run ruff check .
poetry run ruff format .
```

---

## 🔮 Roadmap

* Optional split-per-conversation output
* Markdown-to-embedding JSON transforms
* CLI flags for time-window filtering and topic grouping
* Integration with FileKitty for context-aware imports

---

## 🛡️ License

MIT (or your preferred license)

---

## 👤 Author

Rob Banagale

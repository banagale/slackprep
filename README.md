# slackprep

Turn Slack conversations into useful data for LLM contexts: 
  - Export a target date range or individual channel or conversation
  - Create useful LLM context with Slack conversations:
     - Adds proper conversational turns (i.e. timestamp, author)
     - Creates embedded image placeholders, along with images that can be uploaded into llm context
     - Converts slackmojis into emojis where possible

## Quick Start

### ⚙️ Setup

This project uses Poetry for dependency management.

```bash
# Clone the repo
git clone git@github.com:banagale/slackprep.git

# Install dependencies
poetry install

# Test command:
poetry run slackprep --help
```

### ⚡ Export a week of slack convos

```bash
# Export everything from last month, clean it up, and prep for an LLM
slackprep fetch-all \
  --start-date 2025-06-01 \
  --end-date   2025-07-07 \
  --cleanup \
  --prep
```

This command pulls ALL accessible channels, DMs, and private groups for a date range, then immediately converts them to
Markdown.

This tool avoids rate limiting, so it may take several minutes or longer depending on the amount of chats involved.

### Getting a Slack Token

For a quick, one-off export, you can generate a temporary token:

1. Go to **[https://api.slack.com/apps](https://api.slack.com/apps)**
2. If you can generate a 12-hour app config api token, do that. It will work.
3. Otherwise:
   a. Create a new app in your workspace.
   b. Navigate to **OAuth & Permissions**.
   c. Add the required scopes under **User Token Scopes**: (`channels:history`, `groups:history`, `im:history`,
   `mpim:history`, `users:read`).
   d. Install the app to your workspace and copy the **User OAuth Token** (`xoxp-...`).

The script will securely prompt for your token if it's not set as an environment variable (`SLACK_API_TOKEN`).

**Result:**

```
data/input/slackdump_all_<timestamp>/         # Raw JSON from slackdump
data/output/slackdump_all_<timestamp>/reassembled_<…>.md
```

Feed the resulting Markdown straight into your favourite summarizer or combine with code, docs or other key context
using [FileKitty](https://github.com/banagale/FileKitty).

-----

## 🎯 Target a single channel / DM

To export just one conversation, use `fetch` with a channel or DM ID.

> Get the channel or DM ID by right-clicking the conversation and choosing **Copy > Copy Link**

```bash
# Export one conversation only, then reassemble
slackprep fetch C08ABCXYZ --prep
```

-----

## 🛠 Advanced / Separate steps

## Use existing slack export ZIP

Already have a Slack export `.zip` file?

```bash
unzip slack-export.zip -d data/input/my_export
slackprep reassemble --input-dir data/input/my_export
```

-----

### Use slackdump yourself

For fine-grained control over the export, you can run `slackdump` directly.

```bash
# Note: slackdump uses the SLACK_API_TOKEN environment variable
export SLACK_API_TOKEN="xoxp-your-token"

slackdump export \
  -time-from 2025-06-01 \
  -time-to   2025-07-07 \
  -o data/input/vacation_catchup_raw/
```

### reassemble later

```bash
slackprep reassemble --input-dir data/input/vacation_catchup_raw/
```

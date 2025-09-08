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

### ⚡ Human-only conversations (filter out bots and automation)

```bash
# Export human conversations only, removing bot spam and CI noise
slackprep fetch-all \
  --start-date 2025-06-01 \
  --end-date   2025-07-07 \
  --cleanup \
  --prep \
  --human-only
```

This removes automated content like CI/CD notifications, bot messages, and advisory feeds - perfect for performance reviews or meaningful conversation analysis.

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

-----

## 🎯 Filtering Options

SlackPrep can filter out automation noise to focus on genuine human conversations:

```bash
# Filter out bot messages only
slackprep reassemble --input-dir data/input/my_export --filter-bots

# Filter out automation channels (CI/CD, alerts, notifications)  
slackprep reassemble --input-dir data/input/my_export --filter-automation-channels

# Filter out automated content patterns (advisories, build logs, etc.)
slackprep reassemble --input-dir data/input/my_export --filter-automated-content

# Apply all filters for pure human conversations
slackprep reassemble --input-dir data/input/my_export --human-only
```

**Results**: Human-only filtering can reduce output size by 90%+ by removing CI/CD noise and focusing on meaningful conversations.

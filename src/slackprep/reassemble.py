import argparse
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(".")
ARCHIVE_EXTENSIONS = {".tar.gz", ".zip", ".tgz", ".gz"}


def load_users(users_path):
    with open(users_path) as f:
        users = json.load(f)
        return {
            u["id"]: u.get("real_name") or u.get("name") or "Unknown"
            for u in users
        }


def is_archive(filename: str) -> bool:
    return any(filename.endswith(ext) for ext in ARCHIVE_EXTENSIONS)


def normalize_links_and_mentions(text: str, user_lookup: dict) -> str:
    # Slack-style links: <https://url|label> → [label](https://url)
    text = re.sub(r"<(https?://[^|>]+)\|([^>]+)>", r"[\2](\1)", text)

    # Mentions: <@USERID> → @Full Name
    def replace_mention(match):
        uid = match.group(1)
        name = user_lookup.get(uid, uid)
        return f"@{name}"

    text = re.sub(r"<@([A-Z0-9]+)>", replace_mention, text)

    # Substitute Slack-style emoji shortcodes like :rolling_on_the_floor_laughing: when possible
    EMOJI_MAP = {
        "smile": "😄",
        "laughing": "😆",
        "rolling_on_the_floor_laughing": "🤣",
        "wink": "😉",
        "thumbsup": "👍",
        "thumbsdown": "👎",
        "thinking_face": "🤔",
        "heart": "❤️",
        "fire": "🔥",
        "eyes": "👀",
        "wave": "👋",
        "tada": "🎉",
        "clap": "👏",
        "poop": "💩",
    }

    def emoji_sub(match):
        name = match.group(1)
        return EMOJI_MAP.get(name, f"[emoji:{name}]")

    text = re.sub(r":([a-zA-Z0-9_+]+):", emoji_sub, text)

    return text.strip()


def reassemble_messages(convo_dirs, user_lookup, absolute_timestamps=False, group_turns=True):
    output = []
    previous_user = None
    current_block = []
    last_ts = None

    def flush_block(name, ts, block):
        if not block or not name or not ts:
            return
        header = f"[{name} — {ts}]\n"
        output.append(header + "\n".join(block) + "\n\n---\n")

    for convo_dir in convo_dirs:
        for json_file in sorted(convo_dir.glob("*.json")):
            with open(json_file) as f:
                messages = json.load(f)
                for msg in messages:
                    user_id = msg.get("user", "")
                    name = user_lookup.get(user_id, "Unknown")
                    ts_raw = float(msg["ts"])
                    ts = datetime.fromtimestamp(ts_raw).strftime(
                        "%Y-%m-%d %H:%M" if absolute_timestamps else "%Y-%m-%d")

                    raw = msg.get("text", "")
                    if "```" in raw:
                        # Fix improperly inlined triple-backtick blocks
                        parts = raw.split("```")
                        new = []
                        for i, part in enumerate(parts):
                            if i % 2 == 0:
                                new.append(normalize_links_and_mentions(part, user_lookup))
                            else:
                                new.append("\n```\n" + part.strip() + "\n```\n")
                        text = "".join(new)
                    else:
                        text = normalize_links_and_mentions(raw, user_lookup)

                    line = text

                    for file in msg.get("files", []):
                        filename = file.get("name", "file")
                        file_id = file.get("id")
                        relative_path = f"__uploads/{file_id}/{filename}"

                        if is_archive(filename):
                            line += f"\n📦 Attached file: [`{filename}`]({relative_path})"
                        else:
                            line += f"\n![{filename}]({relative_path})"

                    if group_turns and name == previous_user:
                        current_block.append("")  # spacing between messages
                        current_block.append(line)
                    else:
                        flush_block(previous_user, last_ts, current_block)
                        current_block = [line]
                        previous_user = name
                        last_ts = ts

    flush_block(previous_user, last_ts, current_block)
    return output


def main():
    parser = argparse.ArgumentParser(description="Reassemble Slack messages into an LLM-friendly Markdown transcript.")
    parser.add_argument("--absolute-timestamps", action="store_true", help="Use full YYYY-MM-DD HH:MM timestamps.")
    parser.add_argument("--all-turns", action="store_true", help="Do not group consecutive messages by speaker.")
    args = parser.parse_args()

    users_path = ROOT / "users.json"
    user_lookup = load_users(users_path)

    convo_dirs = [d for d in ROOT.iterdir() if d.is_dir() and d.name.startswith("mpdm-")]
    transcript = reassemble_messages(
        convo_dirs,
        user_lookup,
        absolute_timestamps=args.absolute_timestamps,
        group_turns=not args.all_turns
    )

    output_path = ROOT / "reassembled_conversation.md"
    with open(output_path, "w") as f:
        f.write("\n".join(transcript))

    print(f"✅ Markdown transcript written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()

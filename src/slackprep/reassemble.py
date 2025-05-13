import json
import re
from datetime import datetime
from pathlib import Path

ARCHIVE_EXTENSIONS = {".tar.gz", ".zip", ".tgz", ".gz"}


def load_users(users_path: Path) -> dict:
    with open(users_path) as f:
        users = json.load(f)
        return {
            u["id"]: u.get("real_name") or u.get("name") or "Unknown"
            for u in users
        }


def is_archive(filename: str) -> bool:
    return any(filename.endswith(ext) for ext in ARCHIVE_EXTENSIONS)


def normalize_links_and_mentions(text: str, user_lookup: dict) -> str:
    text = re.sub(r"<(https?://[^|>]+)\|([^>]+)>", r"[\2](\1)", text)

    def replace_mention(match):
        uid = match.group(1)
        name = user_lookup.get(uid, uid)
        return f"@{name}"

    text = re.sub(r"<@([A-Z0-9]+)>", replace_mention, text)

    EMOJI_MAP = {
        "smile": "😄", "laughing": "😆", "rolling_on_the_floor_laughing": "🤣",
        "wink": "😉", "thumbsup": "👍", "thumbsdown": "👎", "thinking_face": "🤔",
        "heart": "❤️", "fire": "🔥", "eyes": "👀", "wave": "👋", "tada": "🎉",
        "clap": "👏", "poop": "💩"
    }

    def emoji_sub(match):
        name = match.group(1)
        return EMOJI_MAP.get(name, f"[emoji:{name}]")

    return re.sub(r":([a-zA-Z0-9_+]+):", emoji_sub, text).strip()


def reassemble_messages(convo_dirs, user_lookup, absolute_timestamps=False, group_turns=True):
    output_md = []
    output_jsonl = []
    previous_user = None
    current_block = []
    last_ts = None

    def flush_block(name, ts, block):
        if not block or not name or not ts:
            return
        header = f"[{name} — {ts}]\n"
        output_md.append(header + "\n".join(block) + "\n\n---\n")

    for convo_dir in convo_dirs:
        for json_file in sorted(convo_dir.glob("*.json")):
            with open(json_file) as f:
                messages = json.load(f)
                for msg in messages:
                    user_id = msg.get("user", "")
                    name = user_lookup.get(user_id, "Unknown")
                    ts_raw = float(msg["ts"])
                    ts_fmt = "%Y-%m-%d %H:%M" if absolute_timestamps else "%Y-%m-%d"
                    ts = datetime.fromtimestamp(ts_raw).strftime(ts_fmt)

                    raw = msg.get("text", "")
                    if "```" in raw:
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

                    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}

                    def is_image(filename: str) -> bool:
                        return any(filename.lower().endswith(ext) for ext in IMAGE_EXTENSIONS)

                    files = []

                    for file in msg.get("files", []):
                        filename = file.get("name", "file")
                        file_id = file.get("id")
                        relative_path = f"__uploads/{file_id}/{filename}"

                        if is_image(filename):
                            text += f"\n![{filename}]({relative_path})"
                            filetype = "image"
                        else:
                            text += f"\n📦 Attached file: [`{filename}`]({relative_path})"
                            filetype = "file"

                        files.append({"name": filename, "type": filetype, "path": relative_path})
                    if group_turns and name == previous_user:
                        current_block.append("")
                        current_block.append(text)
                    else:
                        flush_block(previous_user, last_ts, current_block)
                        current_block = [text]
                        previous_user = name
                        last_ts = ts

                    output_jsonl.append({
                        "timestamp": datetime.fromtimestamp(ts_raw).isoformat(),
                        "user_id": user_id,
                        "user_name": name,
                        "raw_text": raw,
                        "rendered_text": text,
                        "files": files
                    })

    flush_block(previous_user, last_ts, current_block)
    return output_md, output_jsonl


def write_markdown(lines: list[str], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Markdown transcript written to: {output_path.resolve()}")


def write_jsonl(rows: list[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"✅ JSONL transcript written to: {output_path.resolve()}")

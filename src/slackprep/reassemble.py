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


def load_bot_users(users_path: Path) -> set:
    """Load set of bot user IDs from users.json"""
    with open(users_path) as f:
        users = json.load(f)
        return {
            u["id"] for u in users 
            if u.get("is_bot", False)
        }


def is_automation_channel(channel_name: str) -> bool:
    """Detect channels that are likely automation-heavy"""
    automation_patterns = [
        "notification", "alert", "test", "ci", "deploy", "build", 
        "monitor", "status", "bot", "automation", "nightly"
    ]
    name_lower = channel_name.lower()
    return any(pattern in name_lower for pattern in automation_patterns)


def is_automated_content(text: str) -> bool:
    """Detect messages that appear to be automated content"""
    if not text:
        return False
        
    automation_indicators = [
        # Common automation patterns
        "new advisories found",
        "deployment completed",
        "build succeeded", "build failed",
        "pipeline", "job completed", 
        "alert:", "warning:",
        "automated report",
        # RSS/feed patterns  
        "[emoji:rocket]",
        "🚀 *New", "*New advisories*",
        # CI/CD patterns
        "✅ deployed", "❌ failed",
        "merge request", "pull request merged",
    ]
    
    text_lower = text.lower()
    return any(indicator.lower() in text_lower for indicator in automation_indicators)


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


def reassemble_messages(convo_dirs, user_lookup, absolute_timestamps=False, group_turns=True, 
                       bot_users=None, filter_bots=False, filter_automation_channels=False, filter_automated_content=False):
    output_md = []
    output_jsonl = []
    previous_user = None
    current_block = []
    last_ts = None
    
    # Track content statistics and ToC data
    stats = {
        "channels": 0, "dms": 0, "group_msgs": 0, 
        "filtered_channels": 0, "filtered_bot_msgs": 0, "filtered_content_msgs": 0
    }
    toc_entries = []  # For table of contents

    def flush_block(name, ts, block):
        if not block or not name or not ts:
            return
        header = f"[{name} — {ts}]\n"
        output_md.append(header + "\n".join(block) + "\n\n---\n")

    for convo_dir in convo_dirs:
        # Categorize conversation type
        convo_type = ""
        if convo_dir.name.startswith("D"):
            stats["dms"] += 1
            convo_type = "DM"
        elif convo_dir.name.startswith("mpdm-"):
            stats["group_msgs"] += 1
            convo_type = "Group"
        else:
            stats["channels"] += 1
            convo_type = "Channel"
            
        # Skip automation channels if filtering is enabled
        if filter_automation_channels and is_automation_channel(convo_dir.name):
            print(f"🤖 Skipping automation channel: {convo_dir.name}")
            stats["filtered_channels"] += 1
            continue
            
        # Add conversation header
        convo_display_name = convo_dir.name
        if convo_dir.name.startswith("mpdm-"):
            # Clean up group message names
            convo_display_name = convo_dir.name.replace("mpdm-", "Group: ").replace("--", ", ").replace("-1", "")
        
        section_header = f"\n\n# {convo_type}: {convo_display_name}\n\n"
        section_start_index = len(output_md)
        output_md.append(section_header)
        
        # Track for ToC
        toc_entries.append({
            "name": convo_display_name,
            "type": convo_type,
            "index": section_start_index + 1  # +1 for eventual ToC insertion
        })
            
        for json_file in sorted(convo_dir.glob("*.json")):
            with open(json_file) as f:
                messages = json.load(f)
                for msg in messages:
                    user_id = msg.get("user", "")
                    
                    # Skip bot messages if filtering is enabled
                    if filter_bots and bot_users and user_id in bot_users:
                        stats["filtered_bot_msgs"] += 1
                        continue
                        
                    raw = msg.get("text", "")
                    
                    # Skip automated content if filtering is enabled
                    if filter_automated_content and is_automated_content(raw):
                        stats["filtered_content_msgs"] += 1
                        continue
                    name = user_lookup.get(user_id, "Unknown")
                    ts_raw = float(msg["ts"])
                    ts_fmt = "%Y-%m-%d %H:%M" if absolute_timestamps else "%Y-%m-%d"
                    ts = datetime.fromtimestamp(ts_raw).strftime(ts_fmt)

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
    
    # Print content summary
    total_convos = stats["channels"] + stats["dms"] + stats["group_msgs"]
    print(f"📊 Processed {total_convos} conversations: {stats['channels']} channels, {stats['dms']} DMs, {stats['group_msgs']} group messages")
    
    if any(stats[k] for k in ["filtered_channels", "filtered_bot_msgs", "filtered_content_msgs"]):
        print(f"🔽 Filtered out: {stats['filtered_channels']} automation channels, {stats['filtered_bot_msgs']} bot messages, {stats['filtered_content_msgs']} automated content")
    
    return output_md, output_jsonl, toc_entries, stats


def write_markdown(lines: list[str], output_path: Path, toc_entries=None, stats=None):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        # Write header and metadata
        f.write("# Slack Workspace Conversations Export\n\n")
        
        if stats:
            f.write(f"**Export Summary**: {stats['channels']} channels, {stats['dms']} DMs, {stats['group_msgs']} group messages\n")
            if any(stats[k] for k in ["filtered_channels", "filtered_bot_msgs", "filtered_content_msgs"]):
                f.write(f"**Filtered**: {stats['filtered_channels']} automation channels, {stats['filtered_bot_msgs']} bot messages, {stats['filtered_content_msgs']} automated content\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        
        # Write table of contents
        if toc_entries:
            f.write("## Table of Contents\n\n")
            
            # Group by type
            channels = [e for e in toc_entries if e["type"] == "Channel"]
            dms = [e for e in toc_entries if e["type"] == "DM"] 
            groups = [e for e in toc_entries if e["type"] == "Group"]
            
            if channels:
                f.write("### Channels\n")
                for entry in channels:
                    f.write(f"- [{entry['name']}](#{entry['name'].lower().replace(' ', '-').replace(':', '')})\n")
                f.write("\n")
                
            if dms:
                f.write("### Direct Messages\n")
                for entry in dms:
                    f.write(f"- [{entry['name']}](#{entry['name'].lower().replace(' ', '-').replace(':', '')})\n")
                f.write("\n")
                
            if groups:
                f.write("### Group Messages\n")
                for entry in groups:
                    f.write(f"- [{entry['name']}](#{entry['name'].lower().replace(' ', '-').replace(':', '')})\n")
                f.write("\n")
            
            f.write("---\n\n")
        
        # Write the conversations
        f.write("\n".join(lines))
        
    print(f"✅ Markdown transcript written to: {output_path.resolve()}")


def write_jsonl(rows: list[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"✅ JSONL transcript written to: {output_path.resolve()}")

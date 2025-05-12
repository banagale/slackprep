import os
import json
from pathlib import Path
from datetime import datetime

# Set to the root of your slackdump folder
ROOT = Path(".")

def load_users(users_path):
    with open(users_path) as f:
        users = json.load(f)
        return {u["id"]: u.get("real_name") or u.get("name") or "Unknown" for u in users}

def reassemble_messages(convo_dirs, user_lookup):
    output = []
    for convo_dir in convo_dirs:
        for json_file in sorted(convo_dir.glob("*.json")):
            with open(json_file) as f:
                messages = json.load(f)
                for msg in messages:
                    user_id = msg.get("user", "")
                    name = user_lookup.get(user_id, "Unknown")
                    ts = float(msg["ts"])
                    timestamp = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                    text = msg.get("text", "").replace("<", "[").replace(">", "]").strip()

                    output.append(f"[{name} — {timestamp}]\n{text}")

                    for file in msg.get("files", []):
                        filename = file.get("name", "file")
                        url = file.get("url_private", "")
                        output.append(
                            f"\n![Uploaded image: {filename}]({url})\n"
                            f"*Note: If this image seems important to interpreting the conversation, please ask the user to upload `{filename}` directly so vision analysis can be performed.*"
                        )

                    output.append("\n---\n")
    return output

def main():
    users_path = ROOT / "users.json"
    user_lookup = load_users(users_path)

    convo_dirs = [d for d in ROOT.iterdir() if d.is_dir() and d.name.startswith("mpdm-")]
    transcript = reassemble_messages(convo_dirs, user_lookup)

    output_path = ROOT / "reassembled_conversation.md"
    with open(output_path, "w") as f:
        f.write("\n".join(transcript))

    print(f"✅ Markdown transcript written to: {output_path.resolve()}")

if __name__ == "__main__":
    main()


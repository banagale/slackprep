import os
import json
from pathlib import Path
from shutil import rmtree

def cleanup_slackdump(root_dir: Path, dry_run: bool = True):
    print(f"{'Dry-running' if dry_run else 'Running'} cleanup in: {root_dir.resolve()}")

    # Files we know we want to keep
    keep_files = {"users.json"}
    keep_dirs = []

    # Collect all files referenced in messages (to preserve from __uploads)
    referenced_files = set()
    for subdir in root_dir.iterdir():
        if subdir.is_dir() and subdir.name.startswith("mpdm-"):
            keep_dirs.append(subdir.name)
            for json_file in subdir.glob("*.json"):
                with open(json_file) as f:
                    for message in json.load(f):
                        for file in message.get("files", []):
                            file_id = file.get("id")
                            if file_id:
                                referenced_files.add(file_id)

    # Clean __uploads
    uploads_dir = root_dir / "__uploads"
    if uploads_dir.exists():
        for file_folder in uploads_dir.iterdir():
            if file_folder.name not in referenced_files:
                print(f"🗑️  Deleting unused upload: {file_folder}")
                if not dry_run:
                    rmtree(file_folder)

    # Remove known Slack metadata files if unused
    optional_files = {"channels.json", "dms.json", "groups.json", "mpims.json"}
    for fname in optional_files:
        path = root_dir / fname
        if path.exists() and fname not in keep_files:
            print(f"🗑️  Deleting: {path}")
            if not dry_run:
                path.unlink()

    # Remove empty directories
    for d in root_dir.iterdir():
        if d.is_dir() and not any(d.iterdir()):
            print(f"🧹 Removing empty directory: {d}")
            if not dry_run:
                d.rmdir()

    print("✅ Cleanup complete." if not dry_run else "✅ Dry-run complete. Use --apply to delete.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean up a Slackdump export folder.")
    parser.add_argument("path", type=Path, help="Path to Slackdump folder")
    parser.add_argument("--apply", action="store_true", help="Actually delete files (default is dry-run)")

    args = parser.parse_args()
    cleanup_slackdump(args.path, dry_run=not args.apply)

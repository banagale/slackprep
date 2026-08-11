import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from slackprep.cleanup_slackdump import cleanup_slackdump
from slackprep.reassemble import load_bot_users, load_users, reassemble_messages, write_jsonl, write_markdown

IS_MACOS = platform.system() == "Darwin"
UTC_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"


def check_slackdump_workspace() -> bool:
    """Check if slackdump has any configured workspaces."""
    try:
        result = subprocess.run(
            ["slackdump", "workspace", "list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        # If exit code is 9, it means no authenticated workspaces
        if result.returncode == 9:
            return False
        # If exit code is 0, workspaces exist
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # slackdump not installed
        return False


def suggest_slackdump_setup():
    """Provide helpful guidance for setting up slackdump workspace."""
    print("❌ No slackdump workspace configured.")
    print("\n📋 To set up slackdump authentication:")
    print("   1. Run: slackdump wiz")
    print("   2. Choose 'Workspace' → 'New'")
    print("   3. Select 'Login In Browser' and enter your workspace name")
    print("   4. Complete the browser authentication")
    print("\n   Alternatively, you can use: slackdump workspace new <workspace_name>")
    print("\n💡 After setup, retry your slackprep command.")


def parse_utc_timestamp(value: str) -> str:
    """Validate a Slackdump UTC timestamp while preserving its CLI representation."""
    try:
        datetime.strptime(value, UTC_TIMESTAMP_FORMAT)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected UTC timestamp in YYYY-MM-DDTHH:MM:SS format, got {value!r}"
        ) from exc
    return value


def build_slackdump_export_command(
    output_dir: Path,
    time_from: str,
    time_to: str,
    *,
    channel_id: str | None = None,
    files: bool = False,
    api_config: Path | None = None,
) -> list[str]:
    """Build a bounded Slackdump 4 export command with conservative defaults."""
    start = datetime.strptime(time_from, UTC_TIMESTAMP_FORMAT)
    end = datetime.strptime(time_to, UTC_TIMESTAMP_FORMAT)
    if start >= end:
        raise ValueError("--time-from must be earlier than --time-to")

    command = [
        "slackdump",
        "export",
        "-o",
        str(output_dir),
        "-time-from",
        time_from,
        "-time-to",
        time_to,
        f"-files={'true' if files else 'false'}",
        "-channel-users",
    ]
    if api_config:
        command.extend(["-api-config", str(api_config)])
    if channel_id:
        command.append(channel_id)
    return command


def run_slackdump_export(command: list[str]) -> None:
    """Run Slackdump without exposing workspace credentials."""
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        print("❌ slackdump not found. On macOS, install it with `brew install slackdump`.")
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        if exc.returncode == 4:
            print("❌ Authentication error with slackdump.")
            suggest_slackdump_setup()
        else:
            print(f"❌ slackdump failed with exit code {exc.returncode}.")
        sys.exit(1)


def is_valid_slackdump(path: Path) -> bool:
    if not (path / "users.json").exists():
        return False
    for sub in path.iterdir():
        if sub.is_dir() and not sub.name.startswith("__"):
            if any(sub.glob("*.json")):
                return True
    return False


def extract_timestamp(folder_name: str) -> str:
    try:
        parts = folder_name.split("_")
        if len(parts) >= 3:
            date_part = parts[1]
            time_part = parts[2]
            dt = datetime.strptime(date_part + time_part, "%Y%m%d%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return "unknown"


def find_matching_subfolder(input_root: Path, token: str) -> Path | None:
    matches = [d for d in input_root.iterdir() if d.is_dir() and token in d.name]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        print(f"⚠️ Ambiguous input: '{token}' matches multiple folders:")
        for m in matches:
            print(f" - {m.name}")
        sys.exit(1)
    return None


def resolve_input_dir(cli_input: Path | None, extra_arg: str | None) -> Path:
    input_root = Path("data/input")

    if cli_input:
        if is_valid_slackdump(cli_input):
            return cli_input
        print(f"❌ Provided input path '{cli_input}' is not a valid Slack export folder.")
        sys.exit(1)

    if extra_arg:
        match = find_matching_subfolder(input_root, extra_arg)
        if match and is_valid_slackdump(match):
            return match
        elif match:
            print(f"❌ Matched folder '{match}' is not a valid Slack export folder.")
            sys.exit(1)
        else:
            print(f"❌ No folder found in '{input_root}' matching: '{extra_arg}'")
            sys.exit(1)

    if not input_root.exists():
        print(f"⚠️  Default input directory '{input_root}' does not exist.")
        if input("Would you like to create it? [Y/n]: ").strip().lower() in ("", "y"):
            input_root.mkdir(parents=True)
            print(f"✅ Created input folder at: {input_root.resolve()}")
            print("Please export Slack data using the `slackdump` tool and try again.")
        else:
            print("❌ No valid input folder provided. Exiting.")
        sys.exit(1)

    subdirs = [d for d in input_root.iterdir() if d.is_dir()]
    valid_subdirs = [d for d in subdirs if is_valid_slackdump(d)]
    valid_subdirs.sort(key=lambda d: d.name, reverse=True)

    if len(valid_subdirs) == 1:
        print(f"📁 Found one candidate input folder: {valid_subdirs[0].name}")
        print("✅ Using as Slack export root.")
        return valid_subdirs[0]

    elif len(valid_subdirs) > 1:
        print(f"⚠️ Multiple Slack export folders found in '{input_root}':\n")
        for d in valid_subdirs:
            ts = extract_timestamp(d.name)
            print(f"  - {d.name:<30} ({ts})")
        latest = valid_subdirs[0]
        resp = input(f"\nUse most recent? '{latest.name}' [Y/n]: ").strip().lower()
        if resp in ("", "y"):
            print(f"✅ Using '{latest.name}' as Slack export root.")
            return latest
        else:
            print("❌ Aborted. Please specify input with --input-dir.")
            sys.exit(1)

    print("❌ No valid Slack export folders found in 'data/input'.")
    print("\nEach folder must contain a 'users.json' file and at least one conversation directory.")
    print("To create input data, configure a Slackdump workspace with `slackdump wiz`, then run a bounded export.\n")
    print("For setup help, see the README section: '📝 Preparing Input Data'")
    sys.exit(1)


def generate_output_filename(
    format: str,
    group_turns: bool,
    abs_ts: bool,
    filter_bots: bool = False,
    filter_automation_channels: bool = False,
    filter_automated_content: bool = False,
) -> str:
    mode = "allturns" if not group_turns else "grouped"
    if abs_ts:
        mode += "_abs"

    # Add filtering indicators to filename
    if filter_bots or filter_automation_channels or filter_automated_content:
        filter_parts = []
        if filter_bots:
            filter_parts.append("nobots")
        if filter_automation_channels:
            filter_parts.append("nochannelautomation")
        if filter_automated_content:
            filter_parts.append("nocontentautomation")
        mode += "_" + "_".join(filter_parts)

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M")
    ext = "jsonl" if format == "jsonl" else "md"
    return f"workspace_conversations_{mode}_{timestamp}.{ext}"


def link_or_copy_uploads(
    input_dir: Path, output_dir: Path, copy: bool, referenced_files: list[dict], force_fallback: bool
):
    src = input_dir / "__uploads"
    dest = output_dir / "__uploads"

    if dest.exists():
        if copy:
            if dest.is_symlink() or dest.is_dir():
                print(f"🧹 Removing existing uploads folder: {dest}")
                if dest.is_symlink():
                    dest.unlink()
                else:
                    shutil.rmtree(dest)
            else:
                print(f"❌ Unexpected file at {dest}. Delete it manually.")
                sys.exit(1)
        else:
            print(f"❌ Cannot create symlink. '{dest}' already exists and is not a symlink.")
            sys.exit(1)

    if copy:
        print("📦 Copying only referenced uploads to output...")

        dest.mkdir(parents=True, exist_ok=True)
        copied_count = 0
        missing_count = 0

        for f in referenced_files:
            rel_path = Path(f["path"])
            full_src = input_dir / rel_path
            full_dest = output_dir / rel_path
            full_dest.parent.mkdir(parents=True, exist_ok=True)

            try:
                shutil.copy(full_src, full_dest)
                copied_count += 1
            except FileNotFoundError:
                print(f"⚠️  Missing upload file: {rel_path}")
                missing_count += 1
            except Exception as e:
                print(f"❌ Error copying {rel_path}: {e}")
                missing_count += 1

        print(f"📦 Copied {copied_count} files")
        if missing_count > 0:
            print(f"⚠️  {missing_count} files were missing or couldn't be copied")
    else:
        if not IS_MACOS:
            print("⚠️  You're not on macOS. Symlink creation may fail.")
            print("🧪  Consider using `--copy-uploads` for better portability.\n")
        try:
            os.symlink(src, dest, target_is_directory=True)
            print(f"🔗 Symlinked uploads: {dest} → {src}")
        except Exception as e:
            print(f"❌ Failed to create symlink: {e}")
            if force_fallback:
                print("⚠️ Falling back to --copy-uploads mode...")
                link_or_copy_uploads(
                    input_dir, output_dir, copy=True, referenced_files=referenced_files, force_fallback=False
                )
            else:
                print("👉 Re-run with `--copy-uploads` or `--force-fallback` to recover.")
                sys.exit(1)


def handle_fetch(args):
    channel_id = args.channel_id
    if not channel_id.startswith("C") and not channel_id.startswith("D"):
        print(f"❌ Invalid Slack channel or conversation ID: '{channel_id}'")
        sys.exit(1)

    if not check_slackdump_workspace():
        suggest_slackdump_setup()
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"data/input/slackdump_{channel_id}_{timestamp}")

    try:
        command = build_slackdump_export_command(
            output_dir,
            args.time_from,
            args.time_to,
            channel_id=channel_id,
            files=args.files,
            api_config=args.api_config,
        )
    except ValueError as exc:
        print(f"❌ {exc}")
        sys.exit(2)

    file_mode = "enabled" if args.files else "disabled"
    print(
        f"📤 Exporting {channel_id} from {args.time_from} UTC to {args.time_to} UTC "
        f"with file downloads {file_mode} → {output_dir}"
    )
    run_slackdump_export(command)

    print(f"✅ Export complete. Output written to: {output_dir.resolve()}")

    if args.prep:
        folder_name = output_dir.name
        print(f"⚙️  Running slackprep on: {folder_name}")
        handle_reassemble(
            argparse.Namespace(
                folder_token=folder_name,
                input_dir=None,
                output=None,
                format="markdown",
                all_turns=False,
                absolute_timestamps=False,
                use_symlink_for_attachments=False,
                filter_bots=False,
                filter_automation_channels=False,
                filter_automated_content=False,
                human_only=False,
            )
        )


def handle_reassemble(args):
    input_dir = resolve_input_dir(args.input_dir, args.folder_token)
    user_lookup = load_users(input_dir / "users.json")

    # Handle filtering options
    filter_bots = getattr(args, "filter_bots", False) or getattr(args, "human_only", False)
    filter_automation_channels = getattr(args, "filter_automation_channels", False) or getattr(
        args, "human_only", False
    )
    filter_automated_content = getattr(args, "filter_automated_content", False) or getattr(args, "human_only", False)

    bot_users = None
    if filter_bots:
        bot_users = load_bot_users(input_dir / "users.json")
        print(f"🤖 Filtering out messages from {len(bot_users)} bot users")

    convo_dirs = []
    for d in input_dir.iterdir():
        if not d.is_dir():
            continue
        if d.name.startswith("__") or d.name.startswith(".") or d.name == "reassembled":
            continue
        convo_dirs.append(d)

    if not convo_dirs:
        print(f"⚠️  No message folders found in {input_dir}. Are you sure it contains exported Slack messages?")

    md_lines, jsonl_rows, toc_entries, stats = reassemble_messages(
        convo_dirs,
        user_lookup,
        absolute_timestamps=args.absolute_timestamps,
        group_turns=not args.all_turns,
        bot_users=bot_users,
        filter_bots=filter_bots,
        filter_automation_channels=filter_automation_channels,
        filter_automated_content=filter_automated_content,
    )

    output_root = Path("data/output") / input_dir.name
    output_root.mkdir(parents=True, exist_ok=True)

    if IS_MACOS:
        rel_input = Path(os.path.relpath(input_dir.resolve(), start=output_root.resolve()))
        link_path = output_root / "original_input"
        try:
            if link_path.is_symlink():
                if link_path.resolve(strict=False) != input_dir.resolve():
                    print(f"⚠️  Symlink already exists but points elsewhere: {link_path}")
            elif link_path.exists():
                if not link_path.samefile(input_dir.resolve()):
                    print(f"⚠️  Path already exists but points elsewhere: {link_path}")
            else:
                os.symlink(rel_input, link_path)
                print(f"🔗 Symlinked input folder → {link_path}")
        except Exception as e:
            print(f"⚠️  Failed to create symlink to original input: {e}")
    output_path = args.output

    if not output_path:
        output_path = output_root / generate_output_filename(
            args.format,
            group_turns=not args.all_turns,
            abs_ts=args.absolute_timestamps,
            filter_bots=filter_bots,
            filter_automation_channels=filter_automation_channels,
            filter_automated_content=filter_automated_content,
        )

    if args.format == "jsonl":
        write_jsonl(jsonl_rows, output_path)
    else:
        write_markdown(md_lines, output_path, toc_entries, stats)

    all_files = []
    if args.format == "jsonl":
        for row in jsonl_rows:
            all_files.extend(row.get("files", []))
    else:
        for convo_dir in convo_dirs:
            for json_file in sorted(convo_dir.glob("*.json")):
                with open(json_file) as f:
                    messages = json.load(f)
                    for msg in messages:
                        for fobj in msg.get("files", []):
                            filename = fobj.get("name")
                            file_id = fobj.get("id")
                            if not filename or not file_id:
                                continue
                            rel_path = f"__uploads/{file_id}/{filename}"
                            filetype = (
                                "image"
                                if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
                                else "file"
                            )
                            all_files.append({"name": filename, "type": filetype, "path": rel_path})

    link_or_copy_uploads(
        input_dir,
        output_root,
        copy=not args.use_symlink_for_attachments,
        referenced_files=all_files,
        force_fallback=False,
    )


def handle_fetch_all(args: argparse.Namespace) -> None:
    """Export all accessible conversations through a configured Slackdump workspace."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(f"data/input/slackdump_all_{timestamp}")

    if not check_slackdump_workspace():
        suggest_slackdump_setup()
        sys.exit(1)

    try:
        command = build_slackdump_export_command(
            out_dir,
            args.time_from,
            args.time_to,
            files=args.files,
            api_config=args.api_config,
        )
    except ValueError as exc:
        print(f"❌ {exc}")
        sys.exit(2)

    file_mode = "enabled" if args.files else "disabled"
    print(
        f"📤 Exporting all accessible conversations from {args.time_from} UTC to {args.time_to} UTC "
        f"with file downloads {file_mode} → {out_dir}"
    )
    run_slackdump_export(command)
    print(f"✅ Export complete → {out_dir.resolve()}")

    if args.cleanup:
        print("🧹  Running cleanup on exported data...")
        cleanup_slackdump(root_dir=out_dir, dry_run=False)

    if args.prep:
        print("⚙️  Running reassemble...")
        handle_reassemble(
            argparse.Namespace(
                folder_token=None,
                input_dir=out_dir,
                output=None,
                format=args.format,
                all_turns=args.all_turns,
                absolute_timestamps=False,
                use_symlink_for_attachments=False,
                filter_bots=False,
                filter_automation_channels=False,
                filter_automated_content=False,
                human_only=args.human_only,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(prog="slackprep", description="SlackPrep CLI Toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---------- existing sub-commands (fetch, reassemble) ----------
    fetch_parser = subparsers.add_parser("fetch", help="Fetch single channel / DM with slackdump")
    fetch_parser.add_argument("channel_id", help="Slack channel or DM ID (e.g. C08… or D08…)")
    fetch_parser.add_argument(
        "--time-from",
        dest="time_from",
        type=parse_utc_timestamp,
        required=True,
        help="Oldest message timestamp in UTC (YYYY-MM-DDTHH:MM:SS)",
    )
    fetch_parser.add_argument(
        "--time-to",
        dest="time_to",
        type=parse_utc_timestamp,
        required=True,
        help="Newest message timestamp in UTC (YYYY-MM-DDTHH:MM:SS)",
    )
    fetch_parser.add_argument("--files", action="store_true", help="Download attachments (disabled by default)")
    fetch_parser.add_argument("--api-config", type=Path, help="Conservative Slackdump API configuration file")
    fetch_parser.add_argument("--prep", action="store_true", help="Run reassemble after export")
    fetch_parser.set_defaults(func=handle_fetch)

    # ---------- fetch-all (uses a configured Slackdump workspace) ----------
    fetch_all = subparsers.add_parser("fetch-all", help="Fetch all conversations in a bounded UTC time range")
    fetch_all.add_argument(
        "--time-from",
        dest="time_from",
        type=parse_utc_timestamp,
        required=True,
        help="Oldest message timestamp in UTC (YYYY-MM-DDTHH:MM:SS)",
    )
    fetch_all.add_argument(
        "--time-to",
        dest="time_to",
        type=parse_utc_timestamp,
        required=True,
        help="Newest message timestamp in UTC (YYYY-MM-DDTHH:MM:SS)",
    )
    fetch_all.add_argument("--files", action="store_true", help="Download attachments (disabled by default)")
    fetch_all.add_argument("--api-config", type=Path, help="Conservative Slackdump API configuration file")
    fetch_all.add_argument("--prep", action="store_true", help="Run reassemble automatically after export")
    fetch_all.add_argument("--cleanup", action="store_true", help="Remove empty/unused data before prepping")
    fetch_all.add_argument(
        "--format",
        choices=["markdown", "jsonl"],
        default="markdown",
        help="Output format for --prep",
    )
    fetch_all.add_argument(
        "--all-turns",
        action="store_true",
        help="Disable turn grouping during --prep",
    )
    fetch_all.add_argument(
        "--human-only",
        action="store_true",
        help="Apply all bot and automation filters while prepping",
    )
    fetch_all.set_defaults(func=handle_fetch_all)

    # ---------- reassemble ----------
    re_parser = subparsers.add_parser("reassemble", help="Convert Slack export to Markdown / JSONL")
    re_parser.add_argument("folder_token", nargs="?", help="Substring of folder inside data/input/")
    re_parser.add_argument("--input-dir", type=Path, help="Explicit path to export folder")
    re_parser.add_argument("--output", type=Path, help="Output file path")
    re_parser.add_argument("--format", choices=["markdown", "jsonl"], default="markdown")
    re_parser.add_argument("--all-turns", action="store_true", help="Disable turn grouping")
    re_parser.add_argument("--absolute-timestamps", action="store_true", help="Full timestamps")
    re_parser.add_argument(
        "--use-symlink-for-attachments",
        action="store_true",
        help="Symlink __uploads instead of copying (macOS only)",
    )
    re_parser.add_argument(
        "--filter-bots",
        action="store_true",
        help="Filter out messages from bot users",
    )
    re_parser.add_argument(
        "--filter-automation-channels",
        action="store_true",
        help="Skip channels that appear to be automation-heavy",
    )
    re_parser.add_argument(
        "--filter-automated-content",
        action="store_true",
        help="Filter out messages that appear to be automated content (advisories, CI output, etc.)",
    )
    re_parser.add_argument(
        "--human-only",
        action="store_true",
        help="Enable all filtering: bots, automation channels, and automated content",
    )
    re_parser.set_defaults(func=handle_reassemble)

    # ---------- dispatch ----------
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

import argparse
import sys
from datetime import datetime
from pathlib import Path

from slackprep.reassemble import load_users, reassemble_messages, write_markdown, write_jsonl

DEFAULT_INPUT_DIR = Path("data/input")
DEFAULT_OUTPUT_DIR = Path("data/output")


def prompt_create_input_dir():
    print(f"\n⚠️  Default input directory '{DEFAULT_INPUT_DIR}' does not exist.")
    try:
        choice = input("Would you like to create it? [Y/n]: ").strip().lower()
    except EOFError:
        choice = 'n'

    if choice in ("", "y", "yes"):
        DEFAULT_INPUT_DIR.mkdir(parents=True, exist_ok=True)
        full_path = DEFAULT_INPUT_DIR.resolve()
        print(f"✅ Created input folder at: {full_path}")
        print("Please add your Slack export files (e.g., users.json, mpdm-*) and re-run the command.")
        sys.exit(0)
    else:
        print("❌ No valid input directory provided. Use --input-dir or create 'data/input'.")
        sys.exit(1)


def generate_output_path(format: str, grouped: bool, abs_ts: bool) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M")
    mode = "grouped" if grouped else "allturns"
    if abs_ts:
        mode += "_abs"
    ext = ".jsonl" if format == "jsonl" else ".md"
    filename = f"reassembled_{mode}_{timestamp}{ext}"
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTPUT_DIR / filename


def write_markdown(transcript: list[str], path: Path):
    with open(path, "w") as f:
        f.write("\n".join(transcript))
    print(f"✅ Markdown transcript written to: {path.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="Reassemble Slack messages into LLM-ready formats.")
    parser.add_argument("--input-dir", type=Path, help="Path to Slack export directory (default: data/input)")
    parser.add_argument("--output", type=Path, help="Output file path (auto-named if omitted)")
    parser.add_argument("--format", choices=["markdown", "jsonl"], default="markdown", help="Output format")
    parser.add_argument("--absolute-timestamps", action="store_true", help="Use full YYYY-MM-DD HH:MM timestamps")
    parser.add_argument("--all-turns", action="store_true", help="Do not group consecutive messages by speaker")
    args = parser.parse_args()

    input_dir = args.input_dir or DEFAULT_INPUT_DIR
    if not input_dir.exists():
        if args.input_dir is None:
            prompt_create_input_dir()
        else:
            print(f"❌ Input directory not found: {input_dir}")
            sys.exit(1)

    users_path = input_dir / "users.json"
    if not users_path.exists():
        print(f"❌ Missing users.json in {input_dir}. Aborting.")
        sys.exit(1)

    convo_dirs = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith("mpdm-")]
    if not convo_dirs:
        print(f"❌ No mpdm-* folders found in {input_dir}. Aborting.")
        sys.exit(1)

    user_lookup = load_users(users_path)
    transcript = reassemble_messages(
        convo_dirs,
        user_lookup,
        absolute_timestamps=args.absolute_timestamps,
        group_turns=not args.all_turns,
    )

    output_path = args.output or generate_output_path(
        format=args.format,
        grouped=not args.all_turns,
        abs_ts=args.absolute_timestamps,
    )

    if args.format == "markdown":
        write_markdown(transcript, output_path)
    elif args.format == "jsonl":
        write_jsonl(transcript, output_path)


if __name__ == "__main__":
    main()

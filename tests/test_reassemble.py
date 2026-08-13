import json
import os
import time
from pathlib import Path

import pytest

from slackprep.reassemble import (
    is_archive,
    is_automated_content,
    is_automation_channel,
    load_bot_users,
    load_users,
    normalize_links_and_mentions,
    reassemble_messages,
    write_jsonl,
    write_markdown,
)


def test_load_users_and_bots(slack_export: Path) -> None:
    assert load_users(slack_export / "users.json") == {
        "UALICE": "Alice Example",
        "UBOB": "Bob Example",
        "UBOT": "Build Bot",
    }
    assert load_bot_users(slack_export / "users.json") == {"UBOT"}


def test_normalize_links_mentions_emoji_and_code() -> None:
    users = {"UALICE": "Alice Example", "UBOB": "Bob Example"}

    assert (
        normalize_links_and_mentions("Hello <@UBOB> :wave: <https://example.com|example>", users)
        == "Hello @Bob Example 👋 [example](https://example.com)"
    )
    assert normalize_links_and_mentions(":custom_emoji:", users) == "[emoji:custom_emoji]"


def test_classifiers() -> None:
    assert is_automation_channel("build-notifications")
    assert not is_automation_channel("customer-success")
    assert is_automated_content("Build succeeded for main")
    assert not is_automated_content("Can someone review this?")
    assert is_archive("messages.tar.gz")
    assert is_archive("messages.zip")
    assert not is_archive("messages.json")


def test_reassemble_groups_turns_without_crossing_conversations(slack_export: Path) -> None:
    users = load_users(slack_export / "users.json")
    markdown, rows, toc, stats = reassemble_messages([slack_export / "general", slack_export / "random"], users)
    rendered = "".join(markdown)

    assert len(rows) == 6
    assert stats == {
        "channels": 2,
        "dms": 0,
        "group_msgs": 0,
        "filtered_channels": 0,
        "filtered_bot_msgs": 0,
        "filtered_content_msgs": 0,
    }
    assert [entry["name"] for entry in toc] == ["general", "random"]
    assert rendered.index("A separate conversation") > rendered.index("# Channel: random")
    assert rendered.count("[Alice Example —") == 2
    assert "Hello @Bob Example 👋 [example](https://example.com)" in rendered
    assert "```\n<@UALICE> stays literal\n```\noutside @Alice Example" in rendered


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="host timezone switching requires time.tzset")
@pytest.mark.parametrize(
    ("absolute_timestamps", "expected_markdown_timestamp"),
    [(False, "2026-01-02 UTC"), (True, "2026-01-02 17:00 UTC")],
)
def test_reassemble_timestamps_are_explicit_utc_and_host_timezone_independent(
    slack_export: Path,
    absolute_timestamps: bool,
    expected_markdown_timestamp: str,
) -> None:
    users = load_users(slack_export / "users.json")
    original_tz = os.environ.get("TZ")
    outputs = []

    try:
        for host_timezone in ("America/Los_Angeles", "Asia/Tokyo"):
            os.environ["TZ"] = host_timezone
            time.tzset()
            markdown, rows, _, _ = reassemble_messages(
                [slack_export / "general"],
                users,
                absolute_timestamps=absolute_timestamps,
            )
            outputs.append((markdown, rows))
    finally:
        if original_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original_tz
        time.tzset()

    assert outputs[0] == outputs[1]
    markdown, rows = outputs[0]
    assert f"[Alice Example — {expected_markdown_timestamp}]" in "".join(markdown)
    assert rows[0]["timestamp"] == "2026-01-02T17:00:00.000001+00:00"


def test_reassemble_filters_bots_channels_and_automated_content(slack_export: Path) -> None:
    users = load_users(slack_export / "users.json")
    markdown, rows, toc, stats = reassemble_messages(
        [slack_export / "general", slack_export / "build-notifications"],
        users,
        bot_users=load_bot_users(slack_export / "users.json"),
        filter_bots=True,
        filter_automation_channels=True,
        filter_automated_content=True,
    )

    assert len(rows) == 3
    assert all(row["user_id"] != "UBOT" for row in rows)
    assert [entry["name"] for entry in toc] == ["general"]
    assert stats["filtered_channels"] == 1
    assert stats["filtered_bot_msgs"] == 1
    assert "Build succeeded" not in "".join(markdown)


def test_write_markdown_and_jsonl(tmp_path: Path, slack_export: Path) -> None:
    markdown, rows, toc, stats = reassemble_messages(
        [slack_export / "general"], load_users(slack_export / "users.json")
    )
    markdown_path = tmp_path / "out" / "messages.md"
    jsonl_path = tmp_path / "out" / "messages.jsonl"

    write_markdown(markdown, markdown_path, toc, stats)
    write_jsonl(rows, jsonl_path)

    rendered = markdown_path.read_text(encoding="utf-8")
    parsed_rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert "# Slack Workspace Conversations Export" in rendered
    assert "- [general](#general)" in rendered
    assert "# Channel: general" in rendered
    assert "**Generated**:" in rendered
    assert " UTC\n" in rendered
    assert parsed_rows == rows
    assert all(
        {"timestamp", "user_id", "user_name", "raw_text", "rendered_text", "files"} <= row.keys() for row in parsed_rows
    )

import json
from pathlib import Path

import pytest


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def slack_export(tmp_path: Path) -> Path:
    root = tmp_path / "sanitized-export"
    write_json(
        root / "users.json",
        [
            {"id": "UALICE", "name": "alice", "real_name": "Alice Example", "is_bot": False},
            {"id": "UBOB", "name": "bob", "real_name": "Bob Example", "is_bot": False},
            {"id": "UBOT", "name": "buildbot", "real_name": "Build Bot", "is_bot": True},
        ],
    )
    write_json(root / "channels.json", [{"id": "C_GENERAL", "name": "general"}])
    write_json(root / "dms.json", [])
    write_json(root / "groups.json", [])
    write_json(root / "mpims.json", [])
    write_json(
        root / "general" / "2026-01-02.json",
        [
            {
                "type": "message",
                "user": "UALICE",
                "ts": "1767373200.000001",
                "text": "Hello <@UBOB> :wave: <https://example.com|example>",
                "files": [
                    {"id": "F_IMAGE", "name": "diagram.png"},
                    {"id": "F_DOC", "name": "notes.txt"},
                ],
            },
            {
                "type": "message",
                "user": "UALICE",
                "ts": "1767373260.000002",
                "text": "Follow-up",
            },
            {
                "type": "message",
                "user": "UBOB",
                "ts": "1767373320.000003",
                "text": "```<@UALICE> stays literal``` outside <@UALICE>",
            },
            {
                "type": "message",
                "user": "UBOT",
                "ts": "1767373380.000004",
                "text": "Build succeeded",
            },
        ],
    )
    write_json(
        root / "random" / "2026-01-02.json",
        [
            {
                "type": "message",
                "user": "UBOT",
                "ts": "1767373440.000005",
                "text": "A human-written message from a bot account",
            },
            {
                "type": "message",
                "user": "UALICE",
                "ts": "1767373500.000006",
                "text": "A separate conversation",
            },
        ],
    )

    for file_id, filename, content in (
        ("F_IMAGE", "diagram.png", b"not-a-real-image"),
        ("F_DOC", "notes.txt", b"sanitized notes"),
    ):
        upload = root / "__uploads" / file_id / filename
        upload.parent.mkdir(parents=True, exist_ok=True)
        upload.write_bytes(content)

    return root

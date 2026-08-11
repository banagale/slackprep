import json
import os
from pathlib import Path

import pytest

from slackprep.cli import is_valid_slackdump
from slackprep.reassemble import load_users, reassemble_messages


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("SLACKPREP_LIVE_EXPORT"),
    reason="set SLACKPREP_LIVE_EXPORT to a private local Slackdump export",
)
def test_private_export_converts_without_network_access() -> None:
    export = Path(os.environ["SLACKPREP_LIVE_EXPORT"])
    assert is_valid_slackdump(export)

    conversation_dirs = sorted(
        path for path in export.iterdir() if path.is_dir() and not path.name.startswith(("__", "."))
    )
    markdown, rows, toc, stats = reassemble_messages(
        conversation_dirs,
        load_users(export / "users.json"),
    )
    source_message_count = sum(
        len(json.loads(path.read_text(encoding="utf-8")))
        for directory in conversation_dirs
        for path in directory.glob("*.json")
    )

    assert source_message_count > 0
    assert len(rows) == source_message_count
    assert markdown
    assert len(toc) == len(conversation_dirs)
    assert stats["channels"] + stats["dms"] + stats["group_msgs"] == len(conversation_dirs)

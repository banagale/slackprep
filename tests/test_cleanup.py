from pathlib import Path

from slackprep.cleanup_slackdump import cleanup_slackdump


def test_cleanup_preserves_channel_attachments_and_removes_unused_files(
    slack_export: Path,
) -> None:
    unused = slack_export / "__uploads" / "F_UNUSED" / "unused.txt"
    unused.parent.mkdir(parents=True)
    unused.write_text("unused", encoding="utf-8")

    cleanup_slackdump(slack_export, dry_run=False)

    assert (slack_export / "__uploads" / "F_IMAGE" / "diagram.png").exists()
    assert (slack_export / "__uploads" / "F_DOC" / "notes.txt").exists()
    assert not unused.exists()
    assert (slack_export / "users.json").exists()
    assert not (slack_export / "channels.json").exists()


def test_cleanup_dry_run_does_not_delete(slack_export: Path) -> None:
    unused = slack_export / "__uploads" / "F_UNUSED" / "unused.txt"
    unused.parent.mkdir(parents=True)
    unused.write_text("unused", encoding="utf-8")

    cleanup_slackdump(slack_export, dry_run=True)

    assert unused.exists()
    assert (slack_export / "channels.json").exists()

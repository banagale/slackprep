import argparse
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from slackprep import cli


def reassemble_args(input_dir: Path, output: Path, format: str = "markdown") -> argparse.Namespace:
    return argparse.Namespace(
        folder_token=None,
        input_dir=input_dir,
        output=output,
        format=format,
        all_turns=False,
        absolute_timestamps=False,
        use_symlink_for_attachments=False,
        filter_bots=False,
        filter_automation_channels=False,
        filter_automated_content=False,
        human_only=False,
    )


def test_resolve_input_dir_accepts_valid_export(slack_export: Path) -> None:
    assert cli.resolve_input_dir(slack_export, None) == slack_export


def test_handle_reassemble_writes_both_formats_and_copies_attachments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, slack_export: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "IS_MACOS", False)
    markdown_path = tmp_path / "result.md"
    jsonl_path = tmp_path / "result.jsonl"

    cli.handle_reassemble(reassemble_args(slack_export, markdown_path))
    cli.handle_reassemble(reassemble_args(slack_export, jsonl_path, format="jsonl"))

    assert "# Channel: general" in markdown_path.read_text(encoding="utf-8")
    parsed = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert len(parsed) == 6
    output_uploads = tmp_path / "data" / "output" / slack_export.name / "__uploads"
    assert (output_uploads / "F_IMAGE" / "diagram.png").exists()
    assert (output_uploads / "F_DOC" / "notes.txt").exists()


def test_handle_reassemble_reuses_valid_input_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    slack_export: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "IS_MACOS", True)
    output = tmp_path / "result.md"

    cli.handle_reassemble(reassemble_args(slack_export, output))
    cli.handle_reassemble(reassemble_args(slack_export, output))

    link = tmp_path / "data" / "output" / slack_export.name / "original_input"
    assert link.is_symlink()
    assert link.resolve().samefile(slack_export)
    assert "Failed to create symlink" not in capsys.readouterr().out


def test_handle_fetch_invokes_slackdump_for_only_requested_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(cli, "check_slackdump_workspace", lambda: True)
    monkeypatch.setattr(cli.subprocess, "run", run)

    cli.handle_fetch(
        argparse.Namespace(
            channel_id="C01234567",
            time_from="2026-07-13T15:09:00",
            time_to="2026-07-13T17:54:00",
            files=False,
            api_config=Path("throttled.toml"),
            prep=False,
        )
    )

    command = run.call_args.args[0]
    assert command[:2] == ["slackdump", "export"]
    assert command[4:10] == [
        "-time-from",
        "2026-07-13T15:09:00",
        "-time-to",
        "2026-07-13T17:54:00",
        "-files=false",
        "-channel-users",
    ]
    assert command[-3:-1] == ["-api-config", "throttled.toml"]
    assert command[-1] == "C01234567"
    assert run.call_args.kwargs == {"check": True}


def test_handle_fetch_rejects_invalid_conversation_id() -> None:
    with pytest.raises(SystemExit):
        cli.handle_fetch(argparse.Namespace(channel_id="invalid", prep=False))


def test_handle_fetch_all_uses_workspace_and_conservative_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(cli, "check_slackdump_workspace", lambda: True)
    monkeypatch.setattr(cli.subprocess, "run", run)

    cli.handle_fetch_all(
        argparse.Namespace(
            time_from="2026-07-13T15:09:00",
            time_to="2026-07-13T17:54:00",
            files=False,
            api_config=None,
            cleanup=False,
            prep=False,
            format="markdown",
            all_turns=False,
            human_only=False,
        )
    )

    command = run.call_args.args[0]
    assert command[:3] == ["slackdump", "export", "-o"]
    assert command[3].startswith("data/input/slackdump_all_")
    assert command[-2:] == ["-files=false", "-channel-users"]
    assert run.call_args.kwargs == {"check": True}


def test_build_slackdump_export_command_rejects_reversed_time_range() -> None:
    with pytest.raises(ValueError, match="earlier"):
        cli.build_slackdump_export_command(
            Path("output"),
            "2026-07-13T17:54:00",
            "2026-07-13T15:09:00",
        )


def test_parse_utc_timestamp_rejects_date_without_time() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="YYYY-MM-DDTHH:MM:SS"):
        cli.parse_utc_timestamp("2026-07-13")

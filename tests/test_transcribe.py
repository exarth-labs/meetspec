import json
from pathlib import Path

import pytest

from meetings.transcribe import (
    Segment,
    find_inputs,
    fmt_ts,
    meeting_date_and_slug,
    merge_segments,
    slugify,
    speaker_from_filename,
    write_outputs,
)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("audioIkramKhan21234567.m4a", "Ikram Khan"),
        ("audioJohnSmith11.m4a", "John Smith"),
        ("audio_jane_doe42.m4a", "jane doe"),
        ("12345.m4a", "12345"),
    ],
)
def test_speaker_from_filename(filename, expected):
    assert speaker_from_filename(Path(filename)) == expected


def test_meeting_date_comes_from_zoom_folder_name(tmp_path):
    folder = tmp_path / "2026-10-13 18.19.15 Acme Kickoff"
    folder.mkdir()
    assert meeting_date_and_slug(folder) == ("2026-10-13", "acme-kickoff")


def test_meeting_date_falls_back_to_file_date(tmp_path):
    audio = tmp_path / "call.m4a"
    audio.write_bytes(b"x")
    date, slug = meeting_date_and_slug(audio)
    assert len(date) == 10 and date[4] == "-"
    assert slug == "call"


def test_slugify_and_timestamps():
    assert slugify("Ran's Personal Meeting Room") == "ran-s-personal-meeting-room"
    assert slugify("!!!") == "meeting"
    assert fmt_ts(3725.9) == "01:02:05"


def test_merge_joins_close_lines_from_same_speaker():
    merged = merge_segments([
        Segment(0, 2, "A", "Hello"),
        Segment(2.5, 4, "A", "there."),
        Segment(4.2, 5, "B", "Hi."),
        Segment(10, 11, "A", "Later."),
    ])
    assert [(s.speaker, s.text) for s in merged] == [("A", "Hello there."), ("B", "Hi."), ("A", "Later.")]
    assert merged[0].end == 4


def test_find_inputs_uses_per_speaker_audio(tmp_path):
    record = tmp_path / "Audio Record"
    record.mkdir()
    (record / "audioJohnSmith11.m4a").write_bytes(b"x")
    (record / "audioJaneDoe22.m4a").write_bytes(b"x")
    (tmp_path / "video.mp4").write_bytes(b"x" * 100)

    inputs, mode = find_inputs(tmp_path)
    assert mode == "per-speaker"
    assert sorted(speaker for _, speaker in inputs) == ["Jane Doe", "John Smith"]


def test_find_inputs_prefers_audio_only_file(tmp_path):
    (tmp_path / "video.mp4").write_bytes(b"x" * 1000)
    (tmp_path / "audio_only.m4a").write_bytes(b"x")

    inputs, mode = find_inputs(tmp_path)
    assert mode == "single"
    assert inputs == [(tmp_path / "audio_only.m4a", None)]


def test_find_inputs_rejects_empty_folder(tmp_path):
    with pytest.raises(SystemExit):
        find_inputs(tmp_path)


def test_write_outputs(tmp_path):
    meta = {"source_name": "Call", "transcribed_at": "2026-10-13T10:00:00", "mode": "single",
            "model": "tiny", "language": "en", "speakers": ["A"]}
    md, js = write_outputs([Segment(65, 70, "A", "Hello.")], tmp_path, "2026-10-13-call", meta)
    assert "**[00:01:05] A:** Hello." in md.read_text()
    assert json.loads(js.read_text())["segments"][0]["text"] == "Hello."

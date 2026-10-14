import json
from pathlib import Path

import pytest

from meetings import transcribe
from meetings.transcribe import (
    Segment,
    find_inputs,
    fmt_ts,
    glossary_prompt,
    meeting_date_and_slug,
    merge_segments,
    output_name,
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
        ("1-ikram.flac", "ikram"),
        ("Jane Doe.wav", "Jane Doe"),
    ],
)
def test_speaker_from_filename(filename, expected):
    assert speaker_from_filename(Path(filename)) == expected


def test_meeting_date_comes_from_zoom_folder_name(tmp_path):
    folder = tmp_path / "2026-10-13 18.19.15 Ran's Personal Meeting Room"
    folder.mkdir()
    assert meeting_date_and_slug(folder) == ("2026-10-13", "ran-s-personal-meeting-room")


@pytest.mark.parametrize(
    ("filename", "slug"),
    [
        ("Acme sync (2026-10-13 18:19 GMT+5).mp4", "acme-sync"),  # Google Meet
        ("abc-defg-hij (2026-10-13 at 6:19 PM GMT-7).mp4", "abc-defg-hij"),  # Google Meet, no title
        ("Weekly sync-20261013_181915-Meeting Recording.mp4", "weekly-sync"),  # Microsoft Teams
        ("REC_20261013_181915.m4a", "rec"),  # phone recorder
    ],
)
def test_meeting_date_from_other_platforms(tmp_path, filename, slug):
    path = tmp_path / filename
    path.write_bytes(b"x")
    assert meeting_date_and_slug(path) == ("2026-10-13", slug)


def test_invalid_date_in_name_is_ignored(tmp_path):
    path = tmp_path / "notes 2026-13-45.m4a"
    path.write_bytes(b"x")
    date, _ = meeting_date_and_slug(path)
    assert date != "2026-13-45"


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


def test_find_inputs_per_speaker_folder(tmp_path):
    (tmp_path / "1-alice.flac").write_bytes(b"x")
    (tmp_path / "2-bob.flac").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("ignored")

    inputs, mode = find_inputs(tmp_path, per_speaker=True)
    assert mode == "per-speaker"
    assert [speaker for _, speaker in inputs] == ["alice", "bob"]


def test_per_speaker_needs_a_folder_of_tracks(tmp_path):
    (tmp_path / "only.m4a").write_bytes(b"x")
    with pytest.raises(SystemExit):
        find_inputs(tmp_path, per_speaker=True)
    with pytest.raises(SystemExit):
        find_inputs(tmp_path / "only.m4a", per_speaker=True)


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
    assert "Speakers were not separated" in md.read_text()
    data = json.loads(js.read_text())
    assert data["schema"] == "meetspec/transcript/v1"
    assert data["segments"][0] == {"start": 65, "end": 70, "speaker": "A", "text": "Hello."}


def test_merge_keeps_lines_short_when_everyone_shares_a_label():
    # one label for a whole call: back-to-back segments must not become one huge line
    segments = [Segment(i * 5, i * 5 + 4.5, "Speaker", f"Line {i}.") for i in range(30)]
    merged = merge_segments(segments)
    assert len(merged) > 1
    assert all(s.end - s.start <= 30 for s in merged)


def test_zoom_cloud_and_noise_words(tmp_path):
    path = tmp_path / "GMT20261013-131915_Recording_1920x1080.mp4"
    path.write_bytes(b"x")
    assert meeting_date_and_slug(path) == ("2026-10-13", "meeting")


def test_glossary_prompt(tmp_path):
    glossary = tmp_path / "glossary.md"
    glossary.write_text(
        "﻿# Glossary\n\n| Term | Meaning |\n| --- | --- |\n| Acme | client |\n| iSolved | payroll |\n"
        "| Acme | duplicate |\n| | |\n", encoding="utf-8")
    assert glossary_prompt(glossary) == "Acme, iSolved."
    glossary.write_text("| Term | Meaning |\n| --- | --- |\n| | |\n")
    assert glossary_prompt(glossary) is None
    assert glossary_prompt(tmp_path / "missing.md") is None


def test_glossary_prompt_is_capped(tmp_path):
    glossary = tmp_path / "glossary.md"
    glossary.write_text("".join(f"| Term{i:03d} | x |\n" for i in range(200)))
    prompt = glossary_prompt(glossary)
    assert len(prompt) <= 601 and prompt.endswith(".") and not prompt.endswith(",.")


def test_output_name_reuses_same_recording_and_numbers_others(tmp_path):
    meta = {"source_name": "a", "files": ["a.m4a"]}
    assert output_name(tmp_path, "2026-10-13-meeting", meta) == "2026-10-13-meeting"
    (tmp_path / "2026-10-13-meeting.json").write_text(json.dumps({"meta": meta}))
    assert output_name(tmp_path, "2026-10-13-meeting", meta) == "2026-10-13-meeting"
    other = {"source_name": "b", "files": ["b.m4a"]}
    assert output_name(tmp_path, "2026-10-13-meeting", other) == "2026-10-13-meeting-2"


# ---------------------------------------------------------------- main() with a fake model

class FakeInfo:
    duration = 12.0
    language = "en"


class FakeSegment:
    def __init__(self, start, end, text):
        self.start, self.end, self.text = start, end, text


class FakeModel:
    calls: list[dict] = []
    fail: Exception | None = None

    def __init__(self, path, device, compute_type):
        self.compute_type = compute_type

    def transcribe(self, path, **kwargs):
        FakeModel.calls.append(kwargs)
        if FakeModel.fail:
            raise FakeModel.fail
        return iter([FakeSegment(0.0, 4.0, " We need CSV export. "), FakeSegment(5.0, 9.0, "By Friday.")]), FakeInfo()


@pytest.fixture
def fake_whisper(monkeypatch):
    import faster_whisper

    FakeModel.calls, FakeModel.fail = [], None
    monkeypatch.setattr(faster_whisper, "WhisperModel", FakeModel)
    monkeypatch.setattr(transcribe, "model_path", lambda name: "/fake/model")
    return FakeModel


def test_main_uses_glossary_and_prints_json(git_repo, tmp_path, fake_whisper, capsys):
    base = git_repo / ".meetings"
    base.mkdir()
    (base / "glossary.md").write_text("| Term | Meaning |\n| --- | --- |\n| Acme | client |\n")
    recording = tmp_path / "Acme sync (2026-10-13 18:19 GMT+5).m4a"
    recording.write_bytes(b"x")

    transcribe.main([str(recording), "--json"])

    assert fake_whisper.calls[0]["initial_prompt"] == "Acme."
    result = json.loads(capsys.readouterr().out)
    assert result["transcript_json"].endswith("2026-10-13-acme-sync.json")
    data = json.loads(Path(result["transcript_json"]).read_text())
    assert data["meta"]["language"] == "en" and data["meta"]["mode"] == "single"
    assert [s["text"] for s in data["segments"]] == ["We need CSV export. By Friday."]


def test_main_explicit_empty_prompt_disables_glossary(git_repo, tmp_path, fake_whisper):
    (git_repo / ".meetings").mkdir()
    (git_repo / ".meetings" / "glossary.md").write_text("| Acme | client |\n")
    recording = tmp_path / "call.m4a"
    recording.write_bytes(b"x")
    transcribe.main([str(recording), "--prompt", ""])
    assert fake_whisper.calls[0]["initial_prompt"] is None


def test_main_reports_transcription_errors_without_traceback(git_repo, tmp_path, fake_whisper):
    recording = tmp_path / "call.m4a"
    recording.write_bytes(b"x")
    fake_whisper.fail = RuntimeError("CUDA failed: libcudnn not found")
    with pytest.raises(SystemExit) as exc:
        transcribe.main([str(recording), "--device", "cuda"])
    message = str(exc.value.code)
    assert "Could not transcribe call.m4a" in message and "--device cpu" in message


def test_rate_limited_download_suggests_hf_token(monkeypatch):
    import huggingface_hub
    from faster_whisper import utils

    def not_cached(*args, **kwargs):
        raise OSError("not in cache")

    def rate_limited(*args, **kwargs):
        raise RuntimeError("Client error '429 Too Many Requests' for url 'https://huggingface.co/...'")

    monkeypatch.setattr(utils, "download_model", not_cached)
    monkeypatch.setattr(huggingface_hub, "snapshot_download", rate_limited)
    with pytest.raises(SystemExit) as exc:
        transcribe.model_path("tiny.en")
    assert "HF_TOKEN" in str(exc.value.code)

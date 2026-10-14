"""Real transcription with the smallest model. Downloads ~75 MB once, so it only runs with RUN_E2E=1."""

import json
import os
import shutil
from pathlib import Path

import pytest

from meetings import transcribe

pytestmark = pytest.mark.skipif(os.environ.get("RUN_E2E") != "1", reason="set RUN_E2E=1 to run")

FIXTURE = Path(__file__).parent / "fixtures" / "speech.m4a"  # synthetic voice, no real person


def test_transcribes_a_zoom_folder(git_repo, tmp_path):
    (git_repo / ".meetings").mkdir()
    zoom = tmp_path / "2026-10-13 18.19.15 Test Room"
    zoom.mkdir()
    shutil.copy(FIXTURE, zoom / "audio_only.m4a")

    transcribe.main([str(zoom), "--model", "tiny.en"])

    data = json.loads((git_repo / ".meetings" / "transcripts" / "2026-10-13-test-room.json").read_text())
    text = " ".join(s["text"] for s in data["segments"]).lower()
    assert "invoice" in text and "friday" in text
    assert data["meta"]["mode"] == "single"

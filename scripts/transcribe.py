#!/usr/bin/env python3
"""
Local meeting transcription for Zoom recordings (Exarth meeting system).

Everything runs on your own machine: audio never leaves it.

Two input modes:
  1. A Zoom local-recording folder that contains an "Audio Record" subfolder
     (Zoom setting: record a separate audio file for each participant).
     Each file is one speaker, so speakers are labelled by name with no guessing.
  2. A single audio/video file. Speakers are not separated; all lines get one label.

Output (in --out, default ./transcripts):
  <name>.md    readable transcript with timestamps and speakers
  <name>.json  same data, machine-readable (used by the /process-meeting skill)

Examples:
  python scripts/transcribe.py "~/Documents/Zoom/2026-10-14 15.00.00 Acme kickoff"
  python scripts/transcribe.py meeting.m4a --model distil-large-v3
  python scripts/transcribe.py <folder> --prompt "Exarth, Next.js, Stripe, HIPAA, Acme"
  python scripts/transcribe.py <folder> --speakers speakers.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg", ".opus", ".webm", ".mp4", ".mkv", ".mov"}
AUDIO_ONLY_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg", ".opus"}
MERGE_GAP_SECONDS = 1.5


@dataclass
class Segment:
    start: float
    end: float
    speaker: str
    text: str


# ---------------------------------------------------------------- input discovery

def speaker_from_filename(path: Path) -> str:
    """Zoom per-participant files look like 'audioIkramKhan21234567.m4a'.
    Strip the 'audio' prefix and trailing digits, then split CamelCase."""
    stem = path.stem
    name = re.sub(r"^audio", "", stem, flags=re.IGNORECASE)
    name = re.sub(r"\d+$", "", name)
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    name = name.replace("_", " ").strip()
    return name or stem


def is_audio(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in AUDIO_EXTS and not path.name.startswith(".")


def find_inputs(input_path: Path) -> tuple[list[tuple[Path, str | None]], str]:
    """Return ([(file, speaker_or_None)], mode)."""
    if input_path.is_file():
        if not is_audio(input_path):
            sys.exit(f"Not a supported audio/video file: {input_path}")
        return [(input_path, None)], "single"

    if not input_path.is_dir():
        sys.exit(f"Path not found: {input_path}")

    per_speaker_dir = next(
        (d for d in input_path.iterdir() if d.is_dir() and d.name.lower() == "audio record"), None
    )
    if per_speaker_dir:
        files = sorted(f for f in per_speaker_dir.iterdir() if is_audio(f))
        if files:
            return [(f, speaker_from_filename(f)) for f in files], "per-speaker"

    candidates = [f for f in input_path.iterdir() if is_audio(f)]
    if not candidates:
        sys.exit(f"No audio or video files found in: {input_path}")
    # Prefer an audio-only file (smaller, faster), otherwise the largest file.
    audio_only = [f for f in candidates if f.suffix.lower() in AUDIO_ONLY_EXTS]
    chosen = max(audio_only or candidates, key=lambda f: f.stat().st_size)
    return [(chosen, None)], "single"


def load_speaker_map(path: Path | None) -> dict[str, str]:
    if not path:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"Could not read speaker map {path}: {exc}")
    if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
        sys.exit('Speaker map must be a JSON object of strings, e.g. {"John Smith": "Client - John"}')
    return data


# ---------------------------------------------------------------- transcription

def transcribe_file(model, path: Path, speaker: str, language: str | None,
                    prompt: str | None, vad: bool) -> list[Segment]:
    segments, _info = model.transcribe(
        str(path),
        language=language,
        initial_prompt=prompt,
        vad_filter=vad,
        beam_size=5,
    )
    out: list[Segment] = []
    for s in segments:
        text = s.text.strip()
        if text:
            out.append(Segment(start=float(s.start), end=float(s.end), speaker=speaker, text=text))
    return out


def merge_segments(segments: list[Segment], gap: float = MERGE_GAP_SECONDS) -> list[Segment]:
    """Sort by time and join consecutive lines from the same speaker."""
    merged: list[Segment] = []
    for seg in sorted(segments, key=lambda s: (s.start, s.end)):
        last = merged[-1] if merged else None
        if last and last.speaker == seg.speaker and seg.start - last.end <= gap:
            last.end = max(last.end, seg.end)
            last.text = f"{last.text} {seg.text}"
        else:
            merged.append(Segment(seg.start, seg.end, seg.speaker, seg.text))
    return merged


# ---------------------------------------------------------------- output

def fmt_ts(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:80] or "meeting"


def meeting_date_and_slug(input_path: Path) -> tuple[str, str]:
    """Zoom folders are named like '2026-10-14 15.00.00 Acme kickoff'. Use that date and the rest
    as the slug; otherwise fall back to the file's modified date."""
    source_name = input_path.name if input_path.is_dir() else input_path.stem
    m = re.match(r"(\d{4}-\d{2}-\d{2})(?:[ _T]\d{2}\.\d{2}\.\d{2})?[ _-]*(.*)$", source_name)
    if m:
        return m.group(1), slugify(m.group(2) or source_name)
    return f"{datetime.fromtimestamp(input_path.stat().st_mtime):%Y-%m-%d}", slugify(source_name)


def write_outputs(segments: list[Segment], out_dir: Path, name: str, meta: dict) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{name}.md"
    json_path = out_dir / f"{name}.json"

    lines = [
        f"# Transcript: {meta['source_name']}",
        "",
        f"- Transcribed: {meta['transcribed_at']}",
        f"- Mode: {meta['mode']} | Model: {meta['model']} | Language: {meta['language'] or 'auto'}",
        f"- Speakers: {', '.join(meta['speakers'])}",
        "",
        "> Machine transcript. Words can be wrong, especially names and numbers. "
        "Check the recording at the timestamp before treating a line as a requirement.",
        "",
    ]
    for seg in segments:
        lines.append(f"**[{fmt_ts(seg.start)}] {seg.speaker}:** {seg.text}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    json_path.write_text(
        json.dumps({"meta": meta, "segments": [asdict(s) for s in segments]}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return md_path, json_path


# ---------------------------------------------------------------- main

def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe a Zoom meeting locally with faster-whisper.")
    parser.add_argument("input", type=Path, help="Zoom recording folder or a single audio/video file")
    parser.add_argument("--out", type=Path, default=Path("transcripts"), help="output folder (default: ./transcripts)")
    parser.add_argument("--model", default="large-v3",
                        help="whisper model: large-v3 (best), distil-large-v3 (faster, English), medium, small")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--compute-type", default="default",
                        help="e.g. int8 for CPU, float16 for GPU (default: chosen automatically)")
    parser.add_argument("--language", default="en", help="language code, or 'auto' to detect (default: en)")
    parser.add_argument("--prompt", default=None,
                        help="names and technical words used in the meeting; improves spelling of them")
    parser.add_argument("--speakers", type=Path, default=None,
                        help='JSON map from detected name to label, e.g. {"John Smith": "Client - John"}')
    parser.add_argument("--label", default="Speaker", help="speaker label in single-file mode")
    parser.add_argument("--no-vad", action="store_true", help="disable silence filtering")
    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()
    inputs, mode = find_inputs(input_path)
    speaker_map = load_speaker_map(args.speakers.expanduser() if args.speakers else None)
    language = None if args.language == "auto" else args.language

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is not installed. Run: pip install -r scripts/requirements.txt")

    print(f"Loading model '{args.model}' (first run downloads it once)...", flush=True)
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    all_segments: list[Segment] = []
    for path, detected in inputs:
        raw_name = detected or args.label
        speaker = speaker_map.get(raw_name, raw_name)
        print(f"Transcribing {path.name} as '{speaker}'...", flush=True)
        all_segments.extend(transcribe_file(model, path, speaker, language, args.prompt, not args.no_vad))

    if not all_segments:
        sys.exit("No speech found. Check the recording or try --no-vad.")

    segments = merge_segments(all_segments)
    source_name = input_path.name if input_path.is_dir() else input_path.stem
    meeting_date, slug = meeting_date_and_slug(input_path)
    name = f"{meeting_date}-{slug}"
    meta = {
        "source_name": source_name,
        "transcribed_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "model": args.model,
        "language": language,
        "speakers": sorted({s.speaker for s in segments}),
        "files": [p.name for p, _ in inputs],
    }
    md_path, json_path = write_outputs(segments, args.out.expanduser(), name, meta)
    print(f"Done. {len(segments)} lines.\n  {md_path}\n  {json_path}")


if __name__ == "__main__":
    main()

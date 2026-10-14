"""
Local meeting transcription for any recording: Zoom, Google Meet, Microsoft Teams, Webex,
Riverside, a phone voice memo, or any other audio/video file.

Everything runs on your own machine: audio never leaves it.

Two input modes:
  1. Per speaker: one audio file per person, so lines are labelled by name with no guessing.
     Used automatically for a Zoom folder with an "Audio Record" subfolder, and with
     --per-speaker for any folder of per-person tracks (Riverside, Zencastr, Craig for Discord, ...).
  2. Single: one audio/video file, or the best file in a folder. Speakers are not separated;
     all lines get one label.

The meeting date is read from the file or folder name when it has one (Zoom, Meet and Teams
names do), otherwise from the file's modified date.

Output (in --out; default .meetings/transcripts in the project, or ./transcripts outside one):
  <name>.md    readable transcript with timestamps and speakers
  <name>.json  same data, machine-readable (used by the /process-meeting skill)

Examples:
  meetings transcribe "~/Documents/Zoom/2026-10-14 15.00.00 Acme kickoff"
  meetings transcribe "~/Downloads/Acme sync (2026-10-14 15:00 GMT+5).mp4"
  meetings transcribe ~/Downloads/riverside-tracks --per-speaker
  meetings transcribe meeting.m4a --model distil-large-v3
  meetings transcribe <folder> --prompt "Acme, Next.js, Stripe, HIPAA"
  meetings transcribe <folder> --speakers speakers.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .project import find_base

AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg", ".opus", ".webm", ".mp4", ".mkv", ".mov"}
AUDIO_ONLY_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg", ".opus"}
MERGE_GAP_SECONDS = 1.5
TRANSCRIPT_SCHEMA = "ai-transcripter/transcript/v1"


@dataclass
class Segment:
    start: float
    end: float
    speaker: str
    text: str


def log(message: str) -> None:
    """Progress messages go to stderr so stdout stays clean for results (and --json)."""
    print(message, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- input discovery

def speaker_from_filename(path: Path) -> str:
    """Turn a per-speaker track's file name into a name.
    Zoom: 'audioIkramKhan21234567.m4a'; Craig: '1-ikram.flac'; others: 'Ikram Khan.wav'.
    Strip the 'audio' prefix, leading track numbers and trailing digits, then split CamelCase."""
    stem = path.stem
    name = re.sub(r"^audio", "", stem, flags=re.IGNORECASE)
    name = re.sub(r"^\d+[-_ ]+", "", name)
    name = re.sub(r"\d+$", "", name)
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    name = name.replace("_", " ").strip()
    return name or stem


def is_audio(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in AUDIO_EXTS and not path.name.startswith(".")


def find_inputs(input_path: Path, per_speaker: bool = False) -> tuple[list[tuple[Path, str | None]], str]:
    """Return ([(file, speaker_or_None)], mode)."""
    try:
        return _find_inputs(input_path, per_speaker)
    except PermissionError:
        hint = ""
        if sys.platform == "darwin":
            hint = ("\nmacOS blocks terminal apps from Documents, Desktop and Downloads until you allow it: "
                    "System Settings > Privacy & Security > Files and Folders > your terminal app. "
                    "Quit and reopen the app afterwards, or copy the recording somewhere else.")
        sys.exit(f"Permission denied reading {input_path}{hint}")


def _find_inputs(input_path: Path, per_speaker: bool) -> tuple[list[tuple[Path, str | None]], str]:
    if input_path.is_file():
        if per_speaker:
            sys.exit("--per-speaker needs a folder with one audio file per person.")
        if not is_audio(input_path):
            sys.exit(f"Not a supported audio/video file: {input_path}")
        return [(input_path, None)], "single"

    if not input_path.is_dir():
        sys.exit(f"Path not found: {input_path}")

    if per_speaker:
        files = sorted(f for f in input_path.iterdir() if is_audio(f))
        if len(files) < 2:
            sys.exit(f"--per-speaker needs at least two audio files in: {input_path}")
        return [(f, speaker_from_filename(f)) for f in files], "per-speaker"

    zoom_tracks = next(
        (d for d in input_path.iterdir() if d.is_dir() and d.name.lower() == "audio record"), None
    )
    if zoom_tracks:
        files = sorted(f for f in zoom_tracks.iterdir() if is_audio(f))
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

MODEL_FILES = ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*"]


def model_path(name: str) -> str:
    """Return a local folder for the model, downloading it once with a progress bar.

    faster-whisper hides download progress, so the download is done here instead.
    Models are cached by Hugging Face (~/.cache/huggingface) and shared by every project."""
    if Path(name).expanduser().is_dir():
        return str(Path(name).expanduser())
    from faster_whisper.utils import available_models, download_model

    try:
        return download_model(name, local_files_only=True)
    except ValueError:
        sys.exit(f"Unknown model '{name}'. Use one of: {', '.join(available_models())}, "
                 "or a Hugging Face repo id like Systran/faster-whisper-small.")
    except Exception:  # not in the cache yet
        pass

    import huggingface_hub
    from faster_whisper import utils

    repo_id = name if "/" in name else utils._MODELS[name]
    log(f"Downloading model '{name}' from {repo_id} (one time, cached for later runs)...")
    return huggingface_hub.snapshot_download(repo_id, allow_patterns=MODEL_FILES)


def transcribe_file(model, path: Path, speaker: str, language: str | None,
                    prompt: str | None, vad: bool) -> list[Segment]:
    from tqdm import tqdm

    segments, info = model.transcribe(
        str(path),
        language=language,
        initial_prompt=prompt,
        vad_filter=vad,
        beam_size=5,
    )
    out: list[Segment] = []
    total = max(1, round(info.duration))
    with tqdm(total=total, desc=f"{fmt_ts(0)} / {fmt_ts(total)}", dynamic_ncols=True,
              bar_format="  {desc} {percentage:3.0f}%|{bar}| elapsed {elapsed}, left {remaining}") as bar:
        def advance(to: int) -> None:
            bar.set_description_str(f"{fmt_ts(to)} / {fmt_ts(total)}", refresh=False)
            bar.update(to - bar.n)

        advance(0)
        for s in segments:
            advance(min(total, round(s.end)))
            text = s.text.strip()
            if text:
                out.append(Segment(start=float(s.start), end=float(s.end), speaker=speaker, text=text))
        advance(total)
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


_TIME = r"\d{1,2}[.:]\d{2}(?:[.:]\d{2})?(?:\s*[AaPp][Mm])?"
_ZONE = r"(?:\s*(?:GMT|UTC)(?:[+-]\d{1,2}(?::?\d{2})?)?)?"
DATE_PATTERNS = [
    # Zoom '2026-10-14 15.00.00 Acme', Meet 'Acme (2026-10-14 15:00 GMT+5)' or '(2026-10-14 at 15:00 GMT-7)'
    re.compile(rf"(?P<y>\d{{4}})-(?P<m>\d{{2}})-(?P<d>\d{{2}})(?:(?:[ _T]|\s+at\s+){_TIME})?{_ZONE}"),
    # Teams 'Acme-20261014_150000-Meeting Recording', phones 'REC_20261014_150000'
    re.compile(r"(?<!\d)(?P<y>20\d{2})(?P<m>[01]\d)(?P<d>[0-3]\d)(?:[_T-]?\d{4,6})?(?!\d)"),
]
NOISE = re.compile(r"\b(?:meeting recording|recording|audio only|audio_only)\b|\(\s*\)", re.IGNORECASE)


def meeting_date_and_slug(input_path: Path) -> tuple[str, str]:
    """Find the meeting date in the file or folder name (Zoom, Google Meet, Teams and phone
    recordings all put it there) and use the rest of the name as the slug.
    Without a date in the name, use the file's modified date."""
    source_name = input_path.name if input_path.is_dir() else input_path.stem
    for pattern in DATE_PATTERNS:
        for m in pattern.finditer(source_name):
            try:
                found = datetime(int(m["y"]), int(m["m"]), int(m["d"]))
            except ValueError:
                continue
            rest = NOISE.sub(" ", source_name[:m.start()] + " " + source_name[m.end():])
            return f"{found:%Y-%m-%d}", slugify(rest)
    return f"{datetime.fromtimestamp(input_path.stat().st_mtime):%Y-%m-%d}", slugify(NOISE.sub(" ", source_name))


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
    if meta["mode"] == "single":
        lines[-1:-1] = ["> Speakers were not separated in this recording: every line has the same label, "
                        "so who said what has to be inferred from context.", ""]
    for seg in segments:
        lines.append(f"**[{fmt_ts(seg.start)}] {seg.speaker}:** {seg.text}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    json_path.write_text(
        json.dumps({"schema": TRANSCRIPT_SCHEMA, "meta": meta, "segments": [asdict(s) for s in segments]},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return md_path, json_path


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None, prog: str | None = None) -> None:
    parser = argparse.ArgumentParser(prog=prog, description="Transcribe a meeting recording locally with faster-whisper.")
    parser.add_argument("input", type=Path,
                        help="an audio/video file, or a folder with the recording (Zoom, Meet, Teams, ...)")
    parser.add_argument("--per-speaker", action="store_true",
                        help="the folder holds one audio file per person; label lines with names from the file names")
    parser.add_argument("--out", type=Path, default=None,
                        help="output folder (default: .meetings/transcripts in a project, else ./transcripts)")
    parser.add_argument("--model", default="large-v3",
                        help="whisper model: large-v3 (best), distil-large-v3 (faster, English), medium, small")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--compute-type", default=None,
                        help="e.g. int8, float16, float32 (default: int8 on CPU, the model's own type on GPU)")
    parser.add_argument("--language", default="en", help="language code, or 'auto' to detect (default: en)")
    parser.add_argument("--prompt", default=None,
                        help="names and technical words used in the meeting; improves spelling of them")
    parser.add_argument("--speakers", type=Path, default=None,
                        help='JSON map from detected name to label, e.g. {"John Smith": "Client - John"}')
    parser.add_argument("--label", default="Speaker", help="speaker label when speakers are not separated")
    parser.add_argument("--no-vad", action="store_true", help="disable silence filtering")
    parser.add_argument("--json", action="store_true",
                        help="print the result as JSON on stdout (progress still goes to stderr)")
    args = parser.parse_args(argv)
    base = find_base()
    out_dir = args.out.expanduser() if args.out else (base / "transcripts" if base else Path("transcripts"))

    input_path = args.input.expanduser().resolve()
    inputs, mode = find_inputs(input_path, args.per_speaker)
    speaker_map = load_speaker_map(args.speakers.expanduser() if args.speakers else None)
    language = None if args.language == "auto" else args.language

    import ctranslate2
    from faster_whisper import WhisperModel

    compute_type = args.compute_type
    if compute_type is None:
        on_cpu = args.device == "cpu" or (args.device == "auto" and ctranslate2.get_cuda_device_count() == 0)
        compute_type = "int8" if on_cpu else "default"

    path = model_path(args.model)
    log(f"Loading model '{args.model}'...")
    model = WhisperModel(path, device=args.device, compute_type=compute_type)

    all_segments: list[Segment] = []
    for path, detected in inputs:
        raw_name = detected or args.label
        speaker = speaker_map.get(raw_name, raw_name)
        log(f"Transcribing {path.name} as '{speaker}'")
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
        "compute_type": compute_type,
        "language": language,
        "speakers": sorted({s.speaker for s in segments}),
        "files": [p.name for p, _ in inputs],
    }
    md_path, json_path = write_outputs(segments, out_dir, name, meta)
    if args.json:
        print(json.dumps({"transcript_json": str(json_path), "transcript_md": str(md_path),
                          "lines": len(segments), "speakers": meta["speakers"], "mode": mode}, indent=2))
    else:
        print(f"Done. {len(segments)} lines.\n  {md_path}\n  {json_path}")


import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
VENDOR_DIR = BASE_DIR / "vendor"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

import edge_tts

_FILENAME_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_VOICE_PATTERN = re.compile(r"^[A-Za-z]{2,3}-[A-Za-z]{2,4}-[A-Za-z0-9-]{1,96}$")
_MIN_VALUE = -100
_MAX_VALUE = 100
MAX_TEXT_CHARS = 20_000
MAX_VOICE_CHARS = 128
MAX_FILENAME_CHARS = 128
MAX_OUTPUT_FILES = 200
MAX_OUTPUT_BYTES = 512 * 1024 * 1024


def _format_percent(value: int) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value)}%"


def _format_hz(value: int) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value)}Hz"


def _sanitize_filename(stem: str) -> str:
    cleaned = _FILENAME_SAFE_PATTERN.sub("_", stem).strip("._")
    return cleaned or "speech"


def _build_filename(preferred_name: str | None) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if preferred_name:
        safe_name = _sanitize_filename(preferred_name[:MAX_FILENAME_CHARS])
        return f"{safe_name}_{timestamp}.mp3"
    return f"speech_{timestamp}.mp3"


def _validate_voice(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("'voice' must be a string.")
    voice = value.strip()
    if not voice or len(voice) > MAX_VOICE_CHARS or not _VOICE_PATTERN.fullmatch(voice):
        raise ValueError("'voice' is not a supported voice identifier.")
    return voice


def _parse_int_field(payload: dict[str, Any], key: str) -> int:
    raw = payload.get(key, 0)
    if isinstance(raw, bool):
        raise ValueError(f"'{key}' must be an integer.")

    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{key}' must be an integer.") from exc

    if value < _MIN_VALUE or value > _MAX_VALUE:
        raise ValueError(f"'{key}' must be between -100 and 100.")

    return value


def parse_synthesize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object.")

    text_value = payload.get("text", "")
    voice_value = payload.get("voice", "")
    if not isinstance(text_value, str):
        raise ValueError("'text' must be a string.")
    text = text_value.strip()
    voice = _validate_voice(voice_value)
    if not text:
        raise ValueError("'text' is required.")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"'text' must be at most {MAX_TEXT_CHARS} characters.")

    filename = payload.get("filename")
    if filename is not None:
        if not isinstance(filename, str):
            raise ValueError("'filename' must be a string.")
        filename = str(filename).strip() or None

    return {
        "text": text,
        "voice": voice,
        "rate": _parse_int_field(payload, "rate"),
        "volume": _parse_int_field(payload, "volume"),
        "pitch": _parse_int_field(payload, "pitch"),
        "filename": filename,
    }


async def list_voices() -> list[dict[str, str]]:
    raw_voices = await edge_tts.list_voices()
    normalized: list[dict[str, str]] = []

    for item in raw_voices:
        short_name = item.get("ShortName") or item.get("Name") or ""
        if not short_name:
            continue
        normalized.append(
            {
                "short_name": short_name,
                "locale": item.get("Locale", ""),
                "gender": item.get("Gender", ""),
                "friendly_name": item.get("FriendlyName", short_name),
            }
        )

    normalized.sort(key=lambda x: (x["locale"], x["short_name"]))
    return normalized


async def synthesize_to_file(
    *,
    text: str,
    voice: str,
    rate: int,
    volume: int,
    pitch: int,
    filename: str | None = None,
) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("'text' is required.")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"'text' must be at most {MAX_TEXT_CHARS} characters.")
    voice = _validate_voice(voice)
    prune_outputs()
    file_name = _build_filename(filename)
    output_path = OUTPUT_DIR / file_name
    partial_path = output_path.with_name(output_path.name + ".part")

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=_format_percent(rate),
        volume=_format_percent(volume),
        pitch=_format_hz(pitch),
    )
    try:
        await communicate.save(str(partial_path))
        partial_path.replace(output_path)
    finally:
        if partial_path.exists():
            try:
                partial_path.unlink()
            except OSError:
                pass
    prune_outputs()
    return file_name


def prune_outputs() -> None:
    """Keep generated audio bounded so repeated requests cannot fill the disk."""
    files = [
        path
        for path in OUTPUT_DIR.glob("*.mp3")
        if path.is_file() and not path.is_symlink()
    ]
    files.sort(key=lambda path: path.stat().st_mtime_ns)
    total_bytes = sum(path.stat().st_size for path in files)
    while len(files) > MAX_OUTPUT_FILES or total_bytes > MAX_OUTPUT_BYTES:
        oldest = files.pop(0)
        try:
            total_bytes -= oldest.stat().st_size
            oldest.unlink()
        except OSError:
            continue

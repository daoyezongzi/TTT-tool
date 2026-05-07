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
_MIN_VALUE = -100
_MAX_VALUE = 100


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
        safe_name = _sanitize_filename(preferred_name)
        return f"{safe_name}_{timestamp}.mp3"
    return f"speech_{timestamp}.mp3"


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

    text = str(payload.get("text", "")).strip()
    voice = str(payload.get("voice", "")).strip()
    if not text:
        raise ValueError("'text' is required.")
    if not voice:
        raise ValueError("'voice' is required.")

    filename = payload.get("filename")
    if filename is not None:
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
    file_name = _build_filename(filename)
    output_path = OUTPUT_DIR / file_name

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=_format_percent(rate),
        volume=_format_percent(volume),
        pitch=_format_hz(pitch),
    )
    await communicate.save(str(output_path))
    return file_name

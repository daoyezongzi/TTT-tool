import asyncio
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import tts_service
from edge_tts.communicate import mkssml


def test_synthesize_payload_rejects_xml_and_oversized_inputs():
    with pytest.raises(ValueError):
        tts_service.parse_synthesize_payload(
            {"text": "hello", "voice": "en-US-AriaNeural' bad='x"}
        )
    with pytest.raises(ValueError):
        tts_service.parse_synthesize_payload(
            {"text": "x" * (tts_service.MAX_TEXT_CHARS + 1), "voice": "en-US-AriaNeural"}
        )


def test_vendored_ssml_escapes_voice_attribute():
    config = SimpleNamespace(
        voice="en-US-AriaNeural' data='escaped",
        pitch="+0Hz",
        rate="+0%",
        volume="+0%",
    )
    ssml = mkssml(config, "hello")
    assert "name='en-US-AriaNeural&apos; data=&apos;escaped'" in ssml


def test_synthesis_writes_atomically_without_partial_file(monkeypatch):
    class FakeCommunicate:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def save(self, path):
            Path(path).write_bytes(b"audio")

    monkeypatch.setattr(tts_service.edge_tts, "Communicate", FakeCommunicate)
    temp_dir = Path(tempfile.mkdtemp(dir=ROOT / ".runtime_tmp"))
    try:
        monkeypatch.setattr(tts_service, "OUTPUT_DIR", temp_dir)
        file_name = asyncio.run(
            tts_service.synthesize_to_file(
                text="hello",
                voice="en-US-AriaNeural",
                rate=0,
                volume=0,
                pitch=0,
            )
        )
        assert (temp_dir / file_name).read_bytes() == b"audio"
        assert not list(temp_dir.glob("*.part"))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

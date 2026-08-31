import json
import asyncio
import logging
from pathlib import Path

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.tts_service import (
    OUTPUT_DIR,
    list_voices,
    parse_synthesize_payload,
    prune_outputs,
    synthesize_to_file,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR_RESOLVED = OUTPUT_DIR.resolve()
MAX_SYNTHESIS_SECONDS = 120
SYNTHESIS_CONCURRENCY = 2
logger = logging.getLogger(__name__)

jinja_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=select_autoescape(["html", "xml"]),
)


async def index(_: web.Request) -> web.Response:
    template = jinja_env.get_template("index.html")
    return web.Response(text=template.render(), content_type="text/html")


async def get_voices(_: web.Request) -> web.Response:
    try:
        voices = await list_voices()
    except Exception:
        logger.exception("Failed to list TTS voices")
        return web.json_response({"detail": "Unable to list voices."}, status=502)
    return web.json_response({"voices": voices})


async def synthesize(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"detail": "Invalid JSON body."}, status=400)

    try:
        params = parse_synthesize_payload(payload)
        semaphore = request.app["synthesis_semaphore"]
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=1)
        except asyncio.TimeoutError:
            return web.json_response({"detail": "Synthesis capacity is temporarily full."}, status=429)
        try:
            file_name = await asyncio.wait_for(
                synthesize_to_file(**params),
                timeout=MAX_SYNTHESIS_SECONDS,
            )
        finally:
            semaphore.release()
    except ValueError as exc:
        return web.json_response({"detail": str(exc)}, status=400)
    except asyncio.TimeoutError:
        return web.json_response({"detail": "Synthesis timed out."}, status=504)
    except Exception:  # pragma: no cover
        logger.exception("Failed to synthesize audio")
        return web.json_response({"detail": "Failed to synthesize audio."}, status=502)

    return web.json_response(
        {
            "file_name": file_name,
            "download_url": f"/api/download/{file_name}",
        }
    )


async def download_audio(request: web.Request) -> web.StreamResponse:
    file_name = request.match_info["file_name"]
    target = (OUTPUT_DIR / file_name).resolve()

    if OUTPUT_DIR_RESOLVED not in target.parents:
        return web.json_response({"detail": "Invalid file path."}, status=400)
    if not target.exists():
        return web.json_response({"detail": "File not found."}, status=404)

    return web.FileResponse(path=target)


def create_app() -> web.Application:
    app = web.Application(client_max_size=1 * 1024 * 1024)
    app["synthesis_semaphore"] = asyncio.Semaphore(SYNTHESIS_CONCURRENCY)
    prune_outputs()
    app.router.add_get("/", index)
    app.router.add_get("/api/voices", get_voices)
    app.router.add_post("/api/synthesize", synthesize)
    app.router.add_get("/api/download/{file_name}", download_audio)
    app.router.add_static("/static/", path=str(BASE_DIR / "static"), name="static")
    return app


app = create_app()


if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=8000)

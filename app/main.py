import json
from pathlib import Path

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.tts_service import OUTPUT_DIR, list_voices, parse_synthesize_payload, synthesize_to_file

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR_RESOLVED = OUTPUT_DIR.resolve()

jinja_env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=select_autoescape(["html", "xml"]),
)


async def index(_: web.Request) -> web.Response:
    template = jinja_env.get_template("index.html")
    return web.Response(text=template.render(), content_type="text/html")


async def get_voices(_: web.Request) -> web.Response:
    voices = await list_voices()
    return web.json_response({"voices": voices})


async def synthesize(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"detail": "Invalid JSON body."}, status=400)

    try:
        params = parse_synthesize_payload(payload)
        file_name = await synthesize_to_file(**params)
    except ValueError as exc:
        return web.json_response({"detail": str(exc)}, status=400)
    except Exception as exc:  # pragma: no cover
        return web.json_response({"detail": f"Failed to synthesize audio: {exc}"}, status=500)

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
    app = web.Application(client_max_size=4 * 1024 * 1024)
    app.router.add_get("/", index)
    app.router.add_get("/api/voices", get_voices)
    app.router.add_post("/api/synthesize", synthesize)
    app.router.add_get("/api/download/{file_name}", download_audio)
    app.router.add_static("/static/", path=str(BASE_DIR / "static"), name="static")
    return app


app = create_app()


if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=8000)

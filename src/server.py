"""Ronny Kraitman - AI chat web server.

Run from the repo root:
    uvicorn --app-dir src server:app --host 0.0.0.0 --port 8000
"""
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from resume_agent import RESUME_PDF, RonnykAgent

SRC_DIR = Path(__file__).resolve().parent
WEB_DIR = SRC_DIR / "web"
MEDIA_DIR = SRC_DIR / "media"
PUBLIC_DIR = SRC_DIR.parent / "public"

MAX_MESSAGES = 20          # conversation window sent to the model
MAX_MESSAGE_CHARS = 2000   # per-message cap, keeps prompts (and costs) bounded

log = logging.getLogger("ronnyk")
agent: RonnykAgent | None = None


@asynccontextmanager
async def lifespan(_app: Starlette):
    global agent
    agent = RonnykAgent()
    agent.create_an_agent()
    yield


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _sanitize(raw) -> list[dict[str, str]] | None:
    if not isinstance(raw, list) or not raw:
        return None
    clean = []
    for m in raw[-MAX_MESSAGES:]:
        if not isinstance(m, dict):
            return None
        role, content = m.get("role"), m.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str) or not content.strip():
            continue
        clean.append({"role": role, "content": content[:MAX_MESSAGE_CHARS]})
    if not clean or clean[-1]["role"] != "user":
        return None
    return clean


async def index(_request: Request):
    return FileResponse(WEB_DIR / "index.html")


async def resume(_request: Request):
    return FileResponse(
        RESUME_PDF,
        media_type="application/pdf",
        filename="Ronny_Kraitman_Resume.pdf",
        content_disposition_type="attachment",
    )


async def health(_request: Request):
    return JSONResponse({"status": "ok", "model": agent.model_name if agent else None})


async def chat(request: Request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    messages = _sanitize(body.get("messages") if isinstance(body, dict) else None)
    if messages is None:
        return JSONResponse({"error": "messages must end with a user message"}, status_code=400)

    async def event_stream():
        started = time.perf_counter()
        first_token_at = None
        chars = 0
        yield _sse({"type": "start", "model": agent.model_name})
        try:
            async for event in agent.stream(messages):
                if event["type"] == "delta":
                    if first_token_at is None:
                        first_token_at = time.perf_counter()
                    chars += len(event["text"])
                yield _sse(event)
        except Exception:  # noqa: BLE001 - surface a friendly error to the client
            log.exception("agent stream failed")
            yield _sse({"type": "error", "message": "My neurons hit a timeout. Mind trying again?"})
        end = time.perf_counter()
        yield _sse({
            "type": "done",
            "latency_ms": round((end - started) * 1000),
            "ttft_ms": round(((first_token_at or end) - started) * 1000),
            "chars": chars,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/", index),
        Route("/resume", resume),
        Route("/api/health", health),
        Route("/api/chat", chat, methods=["POST"]),
        Mount("/static", StaticFiles(directory=WEB_DIR), name="static"),
        Mount("/media", StaticFiles(directory=MEDIA_DIR), name="media"),
        # keeps the existing https://ronnykraitman.com/public/my_resume.pdf link alive
        Mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public"),
    ],
)

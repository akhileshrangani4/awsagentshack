"""
FastAPI web server for the Conspiracy Board Agent.
Serves the web UI, accepts topic input, runs agent in background thread,
and streams events to browser via WebSocket.
"""
import asyncio
import json
import uuid
import threading
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from agent.agent import run_agent

app = FastAPI(title="Conspiracy Board Agent")

# In-memory store: run_id -> list of events
_runs: dict[str, list[dict]] = {}
_run_complete: dict[str, bool] = {}
_websockets: dict[str, list[WebSocket]] = {}

STATIC_DIR = Path(__file__).parent / "static"


class RunRequest(BaseModel):
    topic_a: str
    topic_b: str
    rounds: int = 3


@app.get("/")
async def index():
    """Serve the main HTML page."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    # Fallback: minimal form if static file doesn't exist yet
    return HTMLResponse("""
    <!DOCTYPE html>
    <html><head><title>Conspiracy Board Agent</title></head>
    <body style="font-family:sans-serif;max-width:600px;margin:40px auto;">
      <h1>Conspiracy Board Agent</h1>
      <form id="f">
        <input name="topic_a" placeholder="Topic A" required style="padding:8px;margin:4px;width:200px;">
        <input name="topic_b" placeholder="Topic B" required style="padding:8px;margin:4px;width:200px;">
        <button type="submit" style="padding:8px 16px;">Investigate</button>
      </form>
      <pre id="log" style="background:#111;color:#0f0;padding:16px;margin-top:16px;max-height:500px;overflow:auto;"></pre>
      <script>
        document.getElementById('f').onsubmit = async (e) => {
          e.preventDefault();
          const fd = new FormData(e.target);
          const res = await fetch('/run', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({topic_a:fd.get('topic_a'),topic_b:fd.get('topic_b'),rounds:3})});
          const {run_id} = await res.json();
          const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
          const ws = new WebSocket(`${wsProto}//${location.host}/ws/${run_id}`);
          const log = document.getElementById('log');
          ws.onmessage = (e) => { log.textContent += e.data + '\\n'; log.scrollTop = log.scrollHeight; };
        };
      </script>
    </body></html>
    """)


@app.post("/run")
async def start_run(req: RunRequest):
    """Start an agent run. Returns run_id for WebSocket connection."""
    run_id = str(uuid.uuid4())[:8]
    _runs[run_id] = []
    _run_complete[run_id] = False
    _websockets[run_id] = []

    def on_event(event: dict):
        _runs[run_id].append(event)
        # Broadcast to all connected websockets for this run
        for ws in list(_websockets.get(run_id, [])):
            try:
                asyncio.run_coroutine_threadsafe(
                    ws.send_json(event),
                    _loop
                )
            except Exception:
                pass

    def run_in_thread():
        try:
            run_agent(req.topic_a, req.topic_b, rounds=req.rounds, on_event=on_event)
        except Exception as e:
            on_event({"type": "error", "message": str(e)})
        finally:
            _run_complete[run_id] = True

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()

    return {"run_id": run_id}


@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """Stream agent events to the browser in real-time."""
    await websocket.accept()

    if run_id not in _runs:
        await websocket.send_json({"type": "error", "message": "Unknown run_id"})
        await websocket.close()
        return

    # Send any events that already happened (client connected late)
    for event in list(_runs.get(run_id, [])):
        await websocket.send_json(event)

    # Register for future events
    _websockets.setdefault(run_id, []).append(websocket)

    try:
        # Keep connection alive until run completes
        while not _run_complete.get(run_id, False):
            try:
                # Use receive with timeout to check completion periodically
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        if run_id in _websockets and websocket in _websockets[run_id]:
            _websockets[run_id].remove(websocket)


# Capture the event loop reference for cross-thread async calls
_loop: asyncio.AbstractEventLoop = None  # type: ignore


@app.on_event("startup")
async def startup():
    global _loop
    _loop = asyncio.get_event_loop()


# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

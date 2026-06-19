from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from jarvis.config import settings
from jarvis.database import init_db
from jarvis.routers import api
from jarvis.services import scheduler, self_modify

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    self_modify.ensure_repo()
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title=settings.agent_name, lifespan=lifespan)
app.include_router(api.router)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", response_class=HTMLResponse)
async def panel():
    return FileResponse(STATIC / "panel.html")

from fastapi import APIRouter, Request
from pydantic import BaseModel

from jarvis.config import settings
from jarvis.services import (
    approvals,
    desktop,
    macos,
    netatmo,
    ollama,
    people,
    planner,
    scheduler,
    self_modify,
    tasks,
)

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str
    source: str = "web"


class ApprovalRequest(BaseModel):
    approved: bool


class NamePersonRequest(BaseModel):
    netatmo_id: str
    name: str
    face_url: str | None = None


class SelfProposeRequest(BaseModel):
    description: str


@router.get("/health")
async def health():
    ollama_status = await ollama.health()
    helper_status = await macos.health()
    key = settings.resolved_cursor_api_key()
    return {
        "agent": settings.agent_name,
        "ollama": ollama_status,
        "macos_helper": helper_status,
        "cursor": {"configured": bool(key)},
        "scheduler": scheduler.status(),
        "port": settings.port,
    }


@router.post("/chat")
async def chat(req: ChatRequest):
    return await planner.handle_message(req.message, source=req.source)


@router.get("/tasks")
async def get_tasks():
    return await tasks.list_tasks()


@router.get("/approvals")
async def get_approvals(status: str | None = None):
    return await approvals.list_approvals(status=status)


@router.post("/approvals/{approval_id}")
async def resolve_approval(approval_id: int, req: ApprovalRequest):
    result = await approvals.resolve_approval(approval_id, req.approved)
    if not result:
        return {"error": "not found"}
    return result


@router.post("/netatmo/webhook")
async def netatmo_webhook(request: Request):
    payload = await request.json()
    return await netatmo.handle_webhook(payload)


@router.get("/people")
async def get_people():
    return await people.list_people()


@router.post("/people/name")
async def name_person(req: NamePersonRequest):
    return await netatmo.name_person(req.netatmo_id, req.name, req.face_url)


@router.delete("/people/{person_id}")
async def forget_person(person_id: int):
    ok = await people.forget_person(person_id)
    return {"ok": ok}


@router.post("/macos/screenshot")
async def take_screenshot():
    return await macos.screenshot()


@router.post("/macos/notify")
async def send_notify(title: str, message: str, speak: bool = False):
    return await macos.notify(title, message, speak=speak)


@router.get("/self/status")
async def self_status():
    return await self_modify.status()


@router.post("/self/propose")
async def self_propose(req: SelfProposeRequest):
    return await self_modify.propose(req.description)


@router.post("/self/test")
async def self_test():
    return await self_modify.run_tests()


@router.post("/desktop/analyze")
async def desktop_analyze():
    return await desktop.analyze_screen()


@router.post("/scheduler/briefing")
async def trigger_briefing():
    await scheduler.morning_briefing()
    return {"ok": True}

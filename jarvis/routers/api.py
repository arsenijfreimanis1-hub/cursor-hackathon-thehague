from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from jarvis.config import settings
from jarvis.services import (
    agent_author,
    agent_registry,
    agent_runtime,
    approvals,
    cursor_trace,
    desktop,
    event_log,
    goal_runner,
    improve_run,
    learning,
    macos,
    memory,
    netatmo,
    notion_sync,
    ollama,
    openclaw,
    people,
    planner,
    scheduler,
    screen_observer,
    security,
    self_modify,
    sessions,
    tasks,
    terminal,
    voice_state,
    worker,
)

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str
    source: str = "web"
    session_id: str | None = None
    speaker_verified: bool | None = None
    speaker_confidence: float | None = None


class ApprovalRequest(BaseModel):
    approved: bool


class NamePersonRequest(BaseModel):
    netatmo_id: str
    name: str
    face_url: str | None = None


class SelfProposeRequest(BaseModel):
    description: str


class MuteRequest(BaseModel):
    muted: bool


class FullAccessRequest(BaseModel):
    enabled: bool


class TerminalRequest(BaseModel):
    command: str


class CreateGoalRequest(BaseModel):
    prompt: str = Field(min_length=3)
    source: str = "web"


class AgentRuntimeRequest(BaseModel):
    execution_engine: str = "cursor"
    autonomy_mode: str = "supervised"
    model: str | None = None
    workspace_dir: str | None = None
    allowed_tools: list[str] = Field(default_factory=lambda: ["cursor_agent.run"])


class CreateAgentRequest(BaseModel):
    name: str | None = None
    purpose: str | None = None
    instructions: str | None = None
    trigger_phrases: list[str] = Field(default_factory=list)
    status: str = "active"
    runtime: AgentRuntimeRequest = Field(default_factory=AgentRuntimeRequest)
    parent_agent_id: int | None = None
    learning_notes: str = ""
    authoring_prompt: str | None = None


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    purpose: str | None = None
    instructions: str | None = None
    trigger_phrases: list[str] | None = None
    status: str | None = None
    runtime: AgentRuntimeRequest | None = None
    parent_agent_id: int | None = None
    learning_notes: str | None = None


class InvokeAgentRequest(BaseModel):
    task: str = Field(min_length=1)
    session_id: str | None = None
    voice: bool = False


@router.get("/dashboard")
async def dashboard():
    """Single fast poll for kiosk — health, voice, active work."""
    helper_status = await macos.health()
    ollama_status = await ollama.health()
    active = await tasks.list_tasks_by_status("running", limit=8)
    queued = await tasks.list_tasks_by_status("queued", limit=8)
    pending_approvals = await approvals.list_approvals(status="pending", limit=20)
    return {
        "agent": settings.agent_name,
        "voice_ui": voice_state.voice_ui_payload(helper_status),
        "ollama": ollama_status,
        "macos_helper": helper_status,
        "worker": worker.status(),
        "security": await security.status(),
        "openclaw": await openclaw.health(),
        "tasks_active": active + queued,
        "approvals_pending": pending_approvals,
        "approval_count": len(pending_approvals),
    }


@router.get("/health")
async def health():
    ollama_status = await ollama.health()
    helper_status = await macos.health()
    key = settings.resolved_cursor_api_key()
    security_status = await security.status()
    openclaw_status = await openclaw.health()
    return {
        "agent": settings.agent_name,
        "ollama": ollama_status,
        "macos_helper": helper_status,
        "voice_ui": voice_state.voice_ui_payload(helper_status),
        "cursor": {"configured": settings.cursor_configured()},
        "openclaw": openclaw_status,
        "scheduler": scheduler.status(),
        "worker": worker.status(),
        "security": security_status,
        "port": settings.port,
    }


@router.post("/chat")
async def chat(req: ChatRequest):
    return await planner.handle_message(
        req.message,
        source=req.source,
        session_id=req.session_id,
        speaker_verified=req.speaker_verified,
        speaker_confidence=req.speaker_confidence,
    )


@router.get("/sessions/{session_id}/messages")
async def session_messages(session_id: str, limit: int = 80):
    return {"messages": await sessions.get_history(session_id, limit=limit)}


@router.get("/tasks/batch/{batch_id}")
async def get_batch_tasks(batch_id: str):
    return await tasks.list_batch_tasks(batch_id)


@router.get("/sessions/active")
async def active_session(source: str | None = None):
    session = await sessions.get_active(source)
    if not session:
        return {"active": False}
    history = await sessions.get_history(session["id"], limit=6)
    return {"active": True, "session": session, "recent": history}


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


@router.post("/macos/mute")
async def set_voice_mute(req: MuteRequest):
    return await macos.set_muted(req.muted)


@router.post("/voice/clear-transcript")
async def voice_clear_transcript():
    return await macos.clear_transcript()


@router.post("/voice/listen")
async def voice_listen():
    return await macos.listen_voice()


@router.post("/voice/ensure-awake")
async def ensure_voice_awake():
    return await macos.ensure_voice_awake()


@router.post("/voice/sleep")
async def voice_sleep():
    return await macos.sleep_voice()


@router.get("/goals/{goal_id}")
async def get_goal(goal_id: int):
    from jarvis.services import goals

    detail = await goals.get_goal_detail(goal_id)
    if not detail:
        raise HTTPException(status_code=404, detail="goal not found")
    return detail


@router.post("/goals")
async def create_goal(req: CreateGoalRequest):
    from jarvis.services import goals

    created = await goals.create_goal_from_prompt(req.prompt, source=req.source)
    return created


@router.get("/agents")
async def list_specialist_agents(status: str | None = None):
    return {"agents": await agent_registry.list_agents(status=status)}


@router.get("/agents/{agent_id}")
async def get_specialist_agent(agent_id: int):
    agent = await agent_registry.get_agent_by_id(agent_id, include_inactive=True)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
    return agent


@router.post("/agents")
async def create_specialist_agent(req: CreateAgentRequest):
    try:
        if req.authoring_prompt:
            created = await agent_author.create_from_prompt(
                req.authoring_prompt,
                workspace_dir=req.runtime.workspace_dir,
                model=req.runtime.model,
            )
        else:
            from jarvis.services.agent_types import AgentSpec

            created = await agent_author.create_from_spec(
                AgentSpec(
                    name=req.name or "",
                    purpose=req.purpose or "",
                    instructions=req.instructions or "",
                    trigger_phrases=req.trigger_phrases,
                    status=req.status,
                    runtime=req.runtime.model_dump(),
                    parent_agent_id=req.parent_agent_id,
                    learning_notes=req.learning_notes,
                )
            )
        return created
    except ValueError as exc:
        detail = str(exc)
        if "already exists" in detail:
            raise HTTPException(status_code=409, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc


@router.patch("/agents/{agent_id}")
async def update_specialist_agent(agent_id: int, req: UpdateAgentRequest):
    try:
        updated = await agent_registry.update_agent(
            agent_id,
            req.model_dump(exclude_none=True),
        )
    except ValueError as exc:
        detail = str(exc)
        if "already exists" in detail:
            raise HTTPException(status_code=409, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="agent not found")
    return updated


@router.post("/agents/{agent_id}/archive")
async def archive_specialist_agent(agent_id: int):
    archived = await agent_registry.archive_agent(agent_id)
    if not archived:
        raise HTTPException(status_code=404, detail="agent not found")
    return archived


@router.post("/agents/{agent_id}/invoke")
async def invoke_specialist_agent(agent_id: int, req: InvokeAgentRequest):
    result = await agent_runtime.invoke_agent(
        agent_id,
        req.task,
        voice=req.voice,
        conversation_id=req.session_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "agent invocation failed"))
    return result


@router.post("/goals/{goal_id}/approve")
async def approve_goal(goal_id: int):
    result = await goal_runner.approve_goal(goal_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "approve failed"))
    return result


@router.get("/security")
async def get_security():
    return await security.status()


@router.post("/security/full-access")
async def set_full_access(req: FullAccessRequest):
    return await security.set_full_access(req.enabled)


@router.post("/terminal/run")
async def run_terminal(req: TerminalRequest):
    full_access = await security.is_full_access()
    result = await terminal.run_command(req.command, full_access=full_access)
    await event_log.log_integration(
        "terminal",
        source="api",
        detail=req.command[:200],
        metadata={"ok": result.get("ok"), "stdout_len": len(result.get("stdout") or "")},
    )
    return result


class StartImproveRunRequest(BaseModel):
    duration_minutes: int = Field(ge=5, le=180, default=30)


@router.post("/self/improve-run/start")
async def start_improve_run(req: StartImproveRunRequest):
    return await improve_run.start(duration_minutes=req.duration_minutes)


@router.post("/self/improve-run/stop")
async def stop_improve_run():
    return await improve_run.stop()


@router.get("/self/improve-run/status")
async def improve_run_status():
    return await improve_run.get_status()


@router.post("/openclaw/reconnect")
async def openclaw_reconnect():
    return await openclaw.ensure_whatsapp()


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


@router.get("/learning/report")
async def get_learning_report():
    return await learning.get_report()


@router.post("/learning/refresh")
async def refresh_learning_report():
    return await learning.update_report(force=True)


@router.get("/memory")
async def get_memory(limit: int = 20):
    return {"entries": await memory.list_recent(limit=limit), "stats": await memory.stats()}


@router.post("/memory/compress")
async def compress_memory():
    return await memory.compress_stale_sessions()


@router.get("/events")
async def get_events(limit: int = 50, source: str | None = None, event_type: str | None = None):
    return {
        "events": await event_log.list_events(limit=limit, source=source, event_type=event_type),
        "stats": await event_log.stats(),
    }


@router.post("/events/export-notion")
async def export_events_notion(limit: int = 40):
    events = await event_log.list_events(limit=limit)
    return await notion_sync.export_recent_events(events)


@router.get("/notion/status")
async def notion_status():
    return {"configured": notion_sync.configured()}


class ScreenEventsRequest(BaseModel):
    events: list[dict] = Field(default_factory=list)


class ScreenContextRequest(BaseModel):
    minutes: int = Field(ge=5, le=180, default=30)
    query: str | None = None
    detail_ids: list[int] = Field(default_factory=list)


@router.post("/screen/events")
async def screen_ingest_events(req: ScreenEventsRequest):
    return await screen_observer.ingest_events(req.events)


@router.get("/screen/status")
async def screen_status():
    helper = await macos.screen_watcher_status()
    observer = await screen_observer.status()
    return {"helper": helper, "observer": observer}


@router.get("/screen/context")
async def screen_context(minutes: int = 30, query: str | None = None, detail_ids: str | None = None):
    ids: list[int] = []
    if detail_ids:
        ids = [int(x) for x in detail_ids.split(",") if x.strip().isdigit()]
    block = await screen_observer.get_recent_context(minutes=minutes, query=query, detail_ids=ids or None)
    return {"context": block}


@router.post("/screen/summarize-now")
async def screen_summarize_now():
    return await screen_observer.observer_tick()


@router.post("/screen/pause")
async def screen_pause():
    return await macos.screen_watcher_pause()


@router.post("/screen/resume")
async def screen_resume():
    return await macos.screen_watcher_resume()


@router.get("/cursor/runs")
async def list_cursor_runs(limit: int = 20, source: str | None = None):
    return {"runs": await cursor_trace.list_runs(limit=limit, source=source)}


@router.get("/cursor/runs/{run_db_id}")
async def get_cursor_run(run_db_id: int):
    run = await cursor_trace.get_run(run_db_id)
    if not run:
        raise HTTPException(status_code=404, detail="cursor run not found")
    return run


@router.get("/cursor/runs/{run_db_id}/transcript")
async def get_cursor_transcript(run_db_id: int):
    text = await cursor_trace.format_transcript(run_db_id)
    if not text:
        raise HTTPException(status_code=404, detail="cursor run not found")
    return {"transcript": text}


@router.post("/desktop/handle-popups")
async def desktop_handle_popups():
    from jarvis.services import popup_handler

    return await popup_handler.handle_popups(full_control=await security.is_full_access())

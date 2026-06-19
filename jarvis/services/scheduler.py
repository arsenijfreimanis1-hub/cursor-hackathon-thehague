from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from jarvis.config import settings
from jarvis.services import approvals, macos, tasks

scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.timezone))


async def morning_briefing() -> None:
    pending = await approvals.list_approvals(status="pending")
    recent = await tasks.list_tasks(limit=5)
    msg = (
        f"Good morning Willy. {len(pending)} items need approval. "
        f"{len(recent)} recent tasks in the queue."
    )
    await macos.notify(settings.agent_name, msg, speak=True)
    await tasks.create_task(title="Morning briefing", body=msg, source="scheduler")


def start() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        morning_briefing,
        "cron",
        hour=settings.briefing_hour,
        minute=0,
        id="morning_briefing",
        replace_existing=True,
    )
    scheduler.start()


def stop() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def status() -> dict:
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })
    return {
        "running": scheduler.running,
        "timezone": settings.timezone,
        "jobs": jobs,
    }

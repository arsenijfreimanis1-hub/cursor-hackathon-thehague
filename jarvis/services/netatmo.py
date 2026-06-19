from jarvis.config import settings
from jarvis.services import approvals, macos, people, tasks


async def handle_webhook(payload: dict) -> dict:
    event_type = payload.get("event_type", "")
    persons = payload.get("persons") or []

    if event_type not in ("person", "human"):
        return {"ok": True, "ignored": event_type}

    await tasks.create_task(
        title=f"Netatmo: {event_type}",
        body=str(payload.get("message", "")),
        source="netatmo",
    )

    if not persons and event_type == "human":
        message = payload.get("message", "Someone detected")
        await macos.notify("William Agent", message)
        return {"ok": True, "action": "human_detected"}

    results = []
    for person in persons:
        netatmo_id = str(person.get("id", ""))
        is_known = bool(person.get("is_known"))
        face_url = person.get("face_url")
        name_hint = payload.get("message", "")

        stored = await people.get_by_netatmo_id(netatmo_id) if netatmo_id else None

        if stored and stored.get("greet_enabled"):
            greeting = f"Welcome home, {stored['name']}!"
            await macos.notify("William Agent", greeting, speak=True)
            await people.mark_seen(netatmo_id, face_url)
            results.append({"person": stored["name"], "action": "greeted"})
            continue

        if is_known and not stored:
            await approvals.request_approval(
                action="store_person",
                detail=f"Netatmo recognized person {netatmo_id}. Name them to remember? ({name_hint})",
            )
            await macos.notify(
                "William Agent",
                f"I see someone familiar. Open the panel to name them.",
            )
            results.append({"person": netatmo_id, "action": "approval_requested"})
            continue

        if not is_known:
            await approvals.request_approval(
                action="store_person",
                detail=f"Unknown person at door. Netatmo ID: {netatmo_id}. Face: {face_url}",
            )
            await macos.notify("William Agent", "Unknown person detected. Open panel to name them.")
            results.append({"person": netatmo_id, "action": "unknown"})
            continue

        await people.mark_seen(netatmo_id, face_url)
        results.append({"person": netatmo_id, "action": "seen"})

    return {"ok": True, "results": results}


async def name_person(netatmo_id: str, name: str, face_url: str | None = None) -> dict:
    person = await people.upsert_person(netatmo_id, name, face_url=face_url, is_known=True)
    await macos.notify("William Agent", f"Got it. I'll greet {name} next time.")
    return person

"""Minis service control: restart, hard reset, and self-update."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

from jarvis.config import ROOT, settings
from jarvis.services import macos, minis, remote_control

HELPER_BUILD = ROOT / "macos-helper" / ".build" / "release" / "JarvisHelper"
HELPER_APP_BIN = ROOT / "macos-helper" / "JarvisHelper.app" / "Contents" / "MacOS" / "JarvisHelper"
STAGING_DIR = settings.data_dir / "minis-updates"
MINIS_HTML = ROOT / "jarvis" / "static" / "minis.html"
RESTART_SCRIPT = ROOT / "scripts" / "restart.sh"
INSTALL_HELPER_SCRIPT = ROOT / "scripts" / "install-helper.sh"


def _uid() -> str:
    return subprocess.check_output(["id", "-u"], text=True).strip()


def _domain_label(label: str) -> str:
    return f"gui/{_uid()}/{label}"


def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["launchctl", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def _kickstart(label: str, *, kill: bool = True) -> dict:
    flag = "-k" if kill else ""
    args = ["kickstart", *([flag] if flag else []), _domain_label(label)]
    result = _launchctl(*args)
    return {
        "ok": result.returncode == 0,
        "label": label,
        "stderr": (result.stderr or "").strip() or None,
    }


def _bootstrap_service(label: str) -> dict:
    plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    if not plist.is_file():
        return {"ok": False, "label": label, "error": f"missing plist: {plist}"}
    domain = f"gui/{_uid()}"
    _launchctl("bootout", _domain_label(label))
    boot = _launchctl("bootstrap", domain, str(plist))
    if boot.returncode != 0:
        return {"ok": False, "label": label, "error": boot.stderr or "bootstrap failed"}
    _launchctl("enable", _domain_label(label))
    start = _launchctl("kickstart", _domain_label(label))
    return {"ok": start.returncode == 0, "label": label, "action": "bootstrapped"}


async def _reset_minis_state() -> None:
    await remote_control.set_enabled(False)
    await minis.set_screen_share(False)


async def restart_services(*, target: str = "both") -> dict:
    """Soft restart via launchctl kickstart -k (helper first, core last)."""

    async def _run() -> None:
        await asyncio.sleep(0.4)
        if target in ("both", "helper"):
            _kickstart("com.willy.jarvis-helper")
            await asyncio.sleep(1.5)
        if target in ("both", "core"):
            _kickstart("com.willy.jarvis-core")

    asyncio.create_task(_run())
    return {"ok": True, "action": "restart_scheduled", "target": target}


async def hard_reset_services() -> dict:
    """Turn off minis toggles, then fully re-register both launchd services."""

    await _reset_minis_state()

    async def _run() -> None:
        await asyncio.sleep(0.4)
        results = []
        for label in ("com.willy.jarvis-helper", "com.willy.jarvis-core"):
            kicked = _kickstart(label)
            if not kicked.get("ok"):
                results.append(_bootstrap_service(label))
            else:
                results.append(kicked)
            await asyncio.sleep(1.0)
        return results

    asyncio.create_task(_run())
    return {"ok": True, "action": "hard_reset_scheduled"}


def _is_mach_o(data: bytes) -> bool:
    if len(data) < 4:
        return False
    magic = int.from_bytes(data[:4], "big")
    return magic in (0xFEEDFACE, 0xFEEDFACF, 0xCEFAEDFE, 0xCFFAEDFE, 0xCAFEBABE)


async def apply_helper_binary(data: bytes) -> dict:
    """Replace installed JarvisHelper binary and restart the helper."""

    if not _is_mach_o(data):
        return {"ok": False, "error": "upload is not a macOS Mach-O binary"}

    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    staged = STAGING_DIR / "JarvisHelper.upload"
    staged.write_bytes(data)
    os.chmod(staged, 0o755)

    targets = [HELPER_BUILD, HELPER_APP_BIN]
    HELPER_BUILD.parent.mkdir(parents=True, exist_ok=True)
    HELPER_APP_BIN.parent.mkdir(parents=True, exist_ok=True)

    for dest in targets:
        shutil.copy2(staged, dest)
        os.chmod(dest, 0o755)
        subprocess.run(
            ["codesign", "--force", "--sign", "-", "--identifier", "com.willy.jarvis-helper", str(dest)],
            capture_output=True,
            check=False,
        )

    restart = _kickstart("com.willy.jarvis-helper")
    return {
        "ok": True,
        "action": "helper_updated",
        "bytes": len(data),
        "paths": [str(p) for p in targets],
        "restart": restart,
    }


async def apply_minis_ui(data: bytes) -> dict:
    MINIS_HTML.write_bytes(data)
    return {"ok": True, "action": "minis_ui_updated", "bytes": len(data), "path": str(MINIS_HTML)}


async def build_helper_from_source() -> dict:
    """Run install-helper.sh to compile and install the helper from local source."""

    if not INSTALL_HELPER_SCRIPT.is_file():
        return {"ok": False, "error": f"missing script: {INSTALL_HELPER_SCRIPT}"}

    async def _run() -> None:
        await asyncio.sleep(0.3)
        subprocess.run(
            ["/bin/bash", str(INSTALL_HELPER_SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )

    asyncio.create_task(_run())
    return {"ok": True, "action": "helper_build_scheduled"}


async def service_info() -> dict:
    helper_path = HELPER_APP_BIN if HELPER_APP_BIN.is_file() else HELPER_BUILD
    return {
        "helper_binary": str(helper_path) if helper_path.is_file() else None,
        "helper_installed": HELPER_APP_BIN.is_file(),
        "core_url": f"http://{settings.host}:{settings.port}",
        "helper_url": settings.macos_helper_url,
        "restart_cli": "./scripts/restart.sh [core|helper|both]",
    }

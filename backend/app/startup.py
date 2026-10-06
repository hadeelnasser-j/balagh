"""Startup tasks that must never prevent the API from starting.

If Supabase is unreachable the server still starts; /api/health then reports
"supabase": "unavailable" and the frontend shows its Arabic notice.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.dependencies.container import Container

logger = logging.getLogger("balagh.startup")

SUPABASE_HINT = (
    "Cannot reach Supabase at %s (%s). The API keeps running and /api/health reports supabase=unavailable. "
    "Check: (1) SUPABASE_URL is the API URL https://<project-ref>.supabase.co from Project Settings > API; "
    "(2) the project is not paused in the Supabase dashboard; (3) this network/VPN/firewall allows HTTPS to "
    "*.supabase.co. Diagnose with: python -m scripts.check_supabase"
)


def recover_stale_jobs(c: "Container", started_before: str) -> None:
    try:
        stale = c.jobs.recover_stale(started_before)
        if stale:
            logger.warning("Marked %d stale processing jobs as failed", stale)
    except Exception as exc:  # noqa: BLE001
        logger.error(SUPABASE_HINT, c.settings.supabase_url, f"{type(exc).__name__}: {exc}")


def run_startup_tasks(c: "Container", background: bool = True) -> list[threading.Thread]:
    started_before = datetime.now(timezone.utc).isoformat()
    tasks = [
        threading.Thread(target=recover_stale_jobs, args=(c, started_before), name="recover-stale-jobs", daemon=True),
        threading.Thread(target=c.sources.ensure_loaded, name="sources-warmup", daemon=True),
    ]
    for t in tasks:
        if background:
            t.start()
        else:
            t.run()
    return tasks

"""Diagnose Supabase connectivity step by step (no keys are printed).

    .venv\\Scripts\\python -m scripts.check_supabase

Steps: URL format -> DNS -> TCP 443 per address -> HTTPS to the REST API -> authenticated query.
"""
from __future__ import annotations

import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.repositories.supabase_repo import url_problem  # noqa: E402


def line(ok: bool | None, text: str) -> None:
    mark = {True: "OK  ", False: "FAIL", None: "INFO"}[ok]
    print(f"[{mark}] {text}", flush=True)


def main() -> int:
    s = get_settings()
    url = s.supabase_url
    print(f"SUPABASE_URL = {url!r}")
    print(f"SUPABASE_SERVICE_ROLE_KEY = {'set (' + str(len(s.supabase_service_role_key)) + ' chars)' if s.supabase_service_role_key else 'NOT SET'}")
    problem = url_problem(url)
    if problem:
        line(False, problem)
        return 1
    host = urlparse(url).hostname or ""
    line(host.endswith(".supabase.co"), f"host {host} " + ("looks like a Supabase project" if host.endswith(".supabase.co")
                                                          else "is not *.supabase.co (custom domain or typo?)"))

    # DNS
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        line(False, f"DNS lookup failed: {exc}. Typo in the project ref, or the project was deleted.")
        return 1
    addrs = sorted({(i[0], i[4][0]) for i in infos}, key=lambda a: a[0] != socket.AF_INET)
    line(True, "DNS: " + ", ".join(f"{'IPv4' if fam == socket.AF_INET else 'IPv6'} {ip}" for fam, ip in addrs))

    # TCP per address
    reachable = []
    for fam, ip in addrs:
        sock = socket.socket(fam, socket.SOCK_STREAM)
        sock.settimeout(6)
        t0 = time.time()
        try:
            sock.connect((ip, 443))
            reachable.append(ip)
            line(True, f"TCP 443 to {ip} in {time.time() - t0:.2f}s")
        except OSError as exc:
            line(False, f"TCP 443 to {ip}: {exc}")
        finally:
            sock.close()
    if not reachable:
        line(False, "No address accepted a connection. This is a network block, not a code problem: "
                    "check firewall/antivirus, VPN/proxy, or try another network (e.g. phone hotspot).")
        try:
            socket.create_connection(("supabase.com", 443), timeout=6).close()
            line(None, "supabase.com IS reachable, so only your project host is blocked/unreachable: "
                       "check the project is not paused (Supabase dashboard > Restore project).")
        except OSError as exc:
            line(None, f"supabase.com is also unreachable ({exc}): the network blocks Supabase entirely.")
        return 1
    if len(reachable) < len(addrs):
        line(None, "Some addresses (often IPv6) fail. If requests hang, disable IPv6 on the adapter or use another network.")

    # HTTPS
    ctx = ssl.create_default_context()
    req = urllib.request.Request(f"{url}/rest/v1/", headers={"apikey": s.supabase_service_role_key,
                                                           "Authorization": f"Bearer {s.supabase_service_role_key}"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            line(True, f"HTTPS REST API answered {resp.status}")
    except urllib.error.HTTPError as exc:
        hint = {401: "key rejected: use the service_role key (Project Settings > API), not the anon key or a JWT secret",
                403: "forbidden: wrong key", 404: "REST API not found at this URL",
                540: "project is PAUSED: restore it in the Supabase dashboard"}.get(exc.code, "")
        line(exc.code < 400, f"HTTPS REST API answered {exc.code} {hint}")
        if exc.code >= 400:
            return 1
    except Exception as exc:  # noqa: BLE001
        line(False, f"HTTPS request failed: {type(exc).__name__}: {exc} "
                    "(TLS interception by antivirus/proxy can cause this)")
        return 1

    # Tables
    try:
        from app.repositories.supabase_repo import SupabaseRepository
        repo = SupabaseRepository(url, s.supabase_service_role_key, s.supabase_timeout_seconds)
        repo.client.table("projects").select("id").limit(1).execute()
        line(True, "query on public.projects succeeded: Supabase is ready")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        hint = " -> run supabase/migrations/001_balagh_schema.sql in the SQL editor" if "projects" in msg or "PGRST" in msg else ""
        line(False, f"query failed: {msg[:300]}{hint}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

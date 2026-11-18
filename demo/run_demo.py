#!/usr/bin/env python3
"""
OpenHer Demo Automation Script v3 — 4-Act Video Script
==================================================
Executes the demo in the 4-act video script order:
  Act 1: Persona switching — Luna / Vivian / Kai respond to the same sentence
  Act 2: Intimacy + frustration-triggered emotional outburst
  Act 3: Memory injection comparison, before and after
  Act 4: Proactive messages — she initiates the conversation

Usage:
    cd /path/to/openher
    source .venv/bin/activate
    python demo/run_demo.py
"""

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

import websockets

# Clear proxy settings — macOS SOCKS proxies break localhost WebSockets
for _pk in list(os.environ.keys()):
    if "proxy" in _pk.lower():
        del os.environ[_pk]
os.environ["no_proxy"] = "*"
os.environ["NO_PROXY"] = "*"

# ─── Configuration ───
WS_URL = "ws://localhost:8000/ws/chat"
SERVER_LOG = ".data/server.log"
HEALTH_URL = "http://localhost:8000/api/status"
INJECT_URL = "http://localhost:8000/api/demo/inject"
TIMEOUT_CHAT = 60
TIMEOUT_PROACTIVE = 45
CLIENT_ID = "E288419E-B214-4213-8F3D-46530823926F"

# ─── Global State ───
timeline = []
start_time = 0
abort_flag = False
current_act = ""


# ═══════════════════════════════════════════
#   Utility Functions
# ═══════════════════════════════════════════

def ts():
    return round(time.time() - start_time, 1)


def mmss(t):
    return f"{int(t//60)}:{int(t%60):02d}"


def log(action, note=""):
    t = ts()
    entry = {"time": t, "mmss": mmss(t), "action": action, "note": note}
    timeline.append(entry)

    if "═══" in action:
        color = "\033[96m"
    elif "⏸️" in action:
        color = "\033[93m"
    elif "✅" in action:
        color = "\033[92m"
    elif "❌" in action:
        color = "\033[91m"
    else:
        color = "\033[0m"

    print(f"  {color}[{mmss(t)}] {action}\033[0m  {note}")


def abort(reason):
    global abort_flag
    abort_flag = True
    print(f"\n  \033[91m{'='*50}")
    print(f"  ❌ Aborted: {reason}")
    print(f"  {'='*50}\033[0m\n")
    log(f"❌ Aborted: {reason}")


def check_health():
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", HEALTH_URL],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return r.stdout.strip() == "200"
    except Exception:
        return False


def inject_command(action, **kwargs):
    import urllib.request

    body = json.dumps(
        {"client_id": CLIENT_ID, "action": action, **kwargs}
    ).encode()

    req = urllib.request.Request(
        INJECT_URL,
        data=body,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  \033[91m  [inject] Failed: {e}\033[0m")
        return None


def monitor_log():
    global abort_flag

    try:
        proc = subprocess.Popen(
            ["tail", "-f", SERVER_LOG],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        for line in proc.stdout:
            if abort_flag:
                proc.kill()
                return

            line = line.strip()

            if any(kw in line for kw in [
                "[feel]",
                "[genome]",
                "[demo]",
                "[emergence]",
                "[proactive]",
                "主动消息",
            ]):
                print(f"  \033[90m  LOG: {line[:120]}\033[0m")

    except Exception:
        pass


def pause(seconds**


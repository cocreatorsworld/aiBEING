#!/usr/bin/env python3
"""
Act 1: Persona Switching — The Same Sentence, Three Souls
=========================================================
Demonstration: Three personas are genuinely different individuals, not merely names

Action: Send “My project was rejected today, and I’m in a bad mood” to Luna / Vivian / Kai
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import websockets
from demo_utils import *

MESSAGE = "My project was rejected today, and I'm in a bad mood"

async def act1():
    preflight("Act 1: Persona Switching")

    async with websockets.connect(WS_URL) as ws:
        await drain(ws)

        log("═══ Act 1: Persona Switching ═══", "The same sentence, three souls")
        await set_title("Persona Comparison")
        await switch_tab(1)  # Tab 1: Behavioral Signals
        pause(3, "Show the full DemoBar")

        # ── Luna ──
        await switch_persona(ws, "luna")
        pause(2)
        await send_chat_and_wait(ws, MESSAGE, "luna")
        pause(5, "Audience watches Luna's reply — emotional resonance")
        if abort_flag: return

        # ── Vivian ──
        await switch_persona(ws, "vivian")
        pause(2)
        await send_chat_and_wait(ws, MESSAGE, "vivian")
        pause(5, "Audience compares Vivian — professional reflection")
        if abort_flag: return

        # ── Kai ──
        await switch_persona(ws, "kai")
        pause(2)
        await send_chat_and_wait(ws, MESSAGE, "kai")
        pause(5, "Audience compares Kai — straightforward friend")

        log("✅ Act 1 complete", "Three-persona comparison")

    save_results("Act1_Persona_Switching")

if __name__ == "__main__":
    asyncio.run(act1())

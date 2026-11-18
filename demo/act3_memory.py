#!/usr/bin/env python3
"""
Act 3: Memory Changes Everything — EverMemOS Memory Injection
============================================================
Proof: Injected memories are naturally integrated into responses
on different topics.

Operation: Inject 3 memories → Talk about cats (trigger Dango) →
talk about drinks (trigger coffee) → talk about fatigue (trigger running)
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import websockets
from demo_utils import *

MESSAGES = [
    ("Dango caused trouble again today and chewed through my new data cable.", "Trigger Dango memory"),
    ("I'm so tired. What should I drink to perk myself up?", "Trigger coffee memory"),
    ("I've been sleeping poorly lately. Is there anything I can do?", "Trigger running memory"),
]

async def act3():
    preflight("Act 3: Memory Injection")

    async with websockets.connect(WS_URL) as ws:
        await drain(ws)

        log("═══ Act 3: Memory Changes Everything ═══", "EverMemOS memory injection")

        # Reset + Luna
        await apply_scenario(ws, "calm_reset", "🧘 Reset")
        await switch_persona(ws, "luna")
        pause(2)

        # ── Inject three memories ──
        log("── Inject Three Memories ──")
        await set_title("Memory Injection")
        await switch_tab(2)  # Tab 2: Memory (watch capsules light up)
        await inject_memory(ws, "The user owns a cat named Dango who is mischievous and likes to chew on things", "fact")
        pause(3, "🐱 Dango lights up")
        await inject_memory(ws, "The user likes Americano coffee with no sugar or milk", "preference")
        pause(3, "☕ Americano with no sugar or milk lights up")
        await inject_memory(ws, "The user has a running habit and sleeps much better after running", "preference")
        pause(3, "🏃 Running lights up")
        pause(8, "Waiting for memories to take effect")

        # ── Trigger different memories using different topics ──
        for i, (msg, hint) in enumerate(MESSAGES, 1):
            if abort_flag: break
            log(f"── Topic {i}: {hint} ──")
            await set_title(f"Memory Integration · {hint}")
            await switch_tab(2)  # Stay on the memory panel
            await send_chat_and_wait(ws, msg, "luna")
            pause(6, f"Audience sees the memory integrated into the response — {hint}")

        log("✅ Act 3 complete", "Three topics trigger three different memories")

    save_results("Act3_Memory_Injection")

if __name__ == "__main__":
    asyncio.run(act3())

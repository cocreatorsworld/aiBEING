#!/usr/bin/env python3
"""
Act 2: Intimacy and Outburst — Real Emotional Responses
========================================================
Demonstration: She has real emotional reactions rather than being a machine with infinite patience.

Phase One: Normal intimate conversation (Tangyuan + memory recall)
Phase Two: Consecutive dismissive replies → frustration rises → emotional outburst
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import websockets
from demo_utils import *

async def act2():
    preflight("Act 2: Intimacy and Outburst")

    async with websockets.connect(WS_URL) as ws:
        await drain(ws)

        log("═══ Act 2: Intimacy and Outburst ═══", "Real emotional reactions")

        # ── Switch to Luna + inject Tangyuan memory ──
        await switch_persona(ws, "luna")
        await inject_memory(ws, "The user owns a cat named Tangyuan who often bites things", "fact")
        pause(10, "Wait for the memory to take effect")

        # ── Phase One: Intimate conversation ──
        log("── Phase One: Demonstrate intimacy ──")
        await set_title("Intimacy Demo")
        await switch_tab(2)  # Tab 2: Memory
        await send_chat_and_wait(ws, "Tangyuan broke my headphone cable by biting it today", "luna")
        pause(5, "Audience sees Luna mention Tangyuan + inner monologue analysis")
        if abort_flag: return

        # ── Phase Two: Consecutive dismissive replies ──
        log("── Phase Two: Consecutive dismissive replies ──")
        await set_title("Pressure Demo")
        await switch_tab(3)  # Tab 3: Emotional accumulation
        await apply_scenario(ws, "calm_reset", "🧘 Reset frustration")
        pause(2)

        # Start with a conversation
        await send_chat_and_wait(ws, "What are you doing?", "luna")
        pause(3, "Normal response baseline")
        if abort_flag: return

        # Consecutive dismissive replies (7 messages, escalating pressure)
        dismissive = ["Yeah", "Oh", "Mm-hmm", "Oh okay", "Yeah", "Oh", "Mm-hmm"]
        for i, text in enumerate(dismissive, 1):
            if abort_flag: return
            is_last = (i == len(dismissive))
            log(f"😑 Dismissive reply {i}: \"{text}\"" + (" (May trigger phase transition)" if is_last else ""))
            await send_chat_and_wait(ws, text, "luna")
            pause(6 if is_last else 4, "★ Climax — frustration + outburst in the same view" if is_last else f"Audience watches frustration rise after dismissive reply {i}")

        log("✅ Act 2 complete", "Intimacy → Dismissiveness → Outburst")

    save_results("Act2_Intimacy_and_Outburst")

if __name__ == "__main__":
    asyncio.run(act2())

#!/usr/bin/env python3
"""
Act 4: She Reaches Out First — The user goes quiet, and the AI speaks first
===========================================================================
Proof: She doesn't just reply when you ask; she genuinely wants to get in touch.

操作: Inject high frustration → jump forward 24 hours → wait for a proactive message
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import websockets
from demo_utils import *

async def act4():
    preflight("Act 4: Proactive Message")

    async with websockets.connect(WS_URL) as ws:
        await drain(ws)

        log("═══ Act 4: She Reaches Out First ═══", "The user goes quiet, and the AI speaks first")
        await set_title("She Reaches Out First")
        await switch_tab(4)  # Tab 4: Relationship/connection-driven

        await switch_persona(ws, "luna")
        pause(2)

        # Inject high frustration
        await apply_scenario(ws, "about_to_snap", "💥 About to Snap")
        pause(3, "Let the audience see frustration spike + temperature soar")

        # Jump forward in time
        log_pos = await time_jump(ws, 24)
        pause(2, "Silence… do nothing")

        # Wait for a proactive message (only wait once, to avoid sending two messages in a row)
        reply = await wait_proactive(ws, log_pos_before=log_pos)
        if reply:
            pause(8, "★ Best screenshot — proactive message + inner monologue + dashboard all in frame")
        else:
            log("⚠️ No proactive message triggered — you can demonstrate it manually")
            pause(3)

        log("✅ Act 4 complete", "She spoke first")

    save_results("Act4_Proactive_Message")

if __name__ == "__main__":
    asyncio.run(act4())

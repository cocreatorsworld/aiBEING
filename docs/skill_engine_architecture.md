# SkillEngine Unified Architecture

> This document describes the complete architecture design of SkillEngine v10, including the two-layer Skill model, Task Skill injection engine, and intrinsic personality Skill paths.

---

## 1. Core Architecture: Two-Layer Skills

SkillEngine unifies all skills into the `SKILL.md` format. At runtime, they are divided into two execution paths:

| Dimension | Task Skill | Intrinsic Personality Skill |
|---|---|---|
| **Trigger** | `tool` | `modality` |
| **Typical examples** | Weather, translation, search, exchange rates | Selfie generation, voice cloning |
| **Trigger mechanism** | LLM function-calling routing (Step -1) | Modality emitted by Actor output (“photo”) |
| **Executor** | `sandbox_executor` (shell commands) | Python handler (`handler_fn` entry point) |
| **Passes through personality engine** | ✅ Injected into `user_message` → full Critic→Actor (Single-Pass) | ✅ Full Critic→Actor (Single-Pass) |
| **Memory writes** | History + EverMemOS (with acknowledged trade-offs) | EverMemOS + Hebbian |
| **Response generation** | Actor Single-Pass (complete personality expression containing real data) | Actor Single-Pass (complete personality expression) |
| **Semantics** | Things the user requests the system to “help with” | Things the character proactively “wants to do” |

### Architectural Evolution: From Bypass to Inject

**v9 (Old)**: Task Skills bypassed the personality engine, used lightweight `_express_wrap` wrapping, and returned early.
- Problem: Weak character tone, loss of concrete data, and broken engine state

**v10 (Current)**: After a Task Skill executes, its stdout is injected into `user_message`, then execution falls through to the personality engine.
- Advantage: Character consistency, data completeness, and normal engine state updates
- Trade-off: History and EverMemOS store synthetic messages containing injected data (see Section 5)

---

## 2. Data Model: L1/L2 Progressive Loading

```text
SKILL.md
├── YAML frontmatter (L1: metadata) ← Batch-loaded by load_all()
│   ├── name, description
│   ├── trigger: modality | tool | cron | manual
│   ├── executor: handler | sandbox
│   ├── handler_fn (Python entry point)
│   └── modality (bound Express modality)
└── Markdown body (L2: instructions) ← Loaded on demand by activate(skill_id)
    └── Complete skill document (handler prompts / shell command examples)
```

- **L1 always loaded**: At startup, read the frontmatter of every `SKILL.md` and construct the `modality_skills` mapping and `tool_skills` list.
- **L2 loaded on demand**: The body may be large, so it is loaded only when the skill is first executed.
- **`activate()` is idempotent**: Repeated calls do not reread the file.

---

## 3. Execution Paths

### Task Skill End-to-End Path (v10 Inject Mode)

```text
"Help me check the weather in Beijing"
  ↓
chat_stream() / _chat_inner() [under turn_lock]
  ↓
Step -1: build_skill_declarations() → [{name:"weather", description:...}]
  ↓
LLM routing: chat([user_msg], tools=[...], tool_choice="auto")
  ↓ tool_calls: [{name:"weather"}]
skill_engine.execute("weather", user_intent, llm)
  ↓
  ├─ skill_id.lower() → normalize capitalization
  ├─ activate("weather") → load body
  ├─ Check whether body is empty
  ├─ LLM([system:skill_document, user:user_request], temperature=0.1) → generate shell command
  ├─ re.sub cleans Markdown code blocks
  ├─ Check whether the command is empty
  └─ sandbox_executor.execute_shell(command, timeout=30)
  ↓
SkillExecutionResult(success=True, output={stdout, stderr, command})
  ↓
Inject stdout into user_message:
  user_message = f"{user_message}\n\n[The following is real query data. It must be naturally incorporated into your response, including key numerical values. Do not omit it]\n{stdout[:800]}"
  ↓
Fall through → Step 0: Critic → Actor (Single-Pass) → Hebbian → EverMemOS
  ↓
The character replies in its own tone while incorporating real data:
"Today's Beijing: +14°C, 47% humidity, 14 km/h wind. It's a pretty good day for a walk~"
```

### Intrinsic Personality Skill Path (Unchanged)

```text
Actor output emits modality="photo"
  ↓
_execute_skill(skill, modality, persona_id, raw_output)
  ↓
Dynamically import handler_fn → call generate_selfie(...)
  ↓
Return image_path and continue through normal Express processing
  ↓
Hebbian learning + EverMemOS memory ✓
```

---

## 4. Guard Clause Design (v10)

```python
async def chat_stream(self, user_message: str) -> AsyncIterator[str]:
    await self._turn_lock.acquire()
    try:
        # ── Step -1: Task skill routing ──
        if self.skill_engine:
            skill_defs = self.skill_engine.build_skill_declarations()
            if skill_defs:
                routing_resp = await self.llm.chat(...)   # Three-layer exception protection
                if routing_resp and routing_resp.tool_calls:
                    result = await self.skill_engine.execute(...)
                    if result is not None:
                        stdout = result.output.get("stdout", "").strip()
                        if stdout:
                            user_message = f"{user_message}\n\n[...]\n{stdout[:800]}"
                            # Do not return; continue to Step 0
                # Fall through regardless of success or failure

        # ── Step 0: Personality engine (unchanged) ──
        self._turn_count += 1
        ...
```

### Inject vs. Old Bypass Comparison

| State variable | v9 bypass | v10 inject |
|---|---|---|
| `_turn_count` | ❌ Not incremented | ✅ Incremented normally |
| `_last_active` | ❌ Not updated | ✅ Updated normally |
| Critic / Actor (Single-Pass) | ❌ Skipped | ✅ Fully executed |
| Hebbian / EverMemOS | ❌ Not triggered | ✅ Triggered normally (with injected data) |
| Lock release | ✅ `finally` | ✅ `finally` |

### Three-Layer Exception Handling

```text
Layer 1: Routing LLM fails → silently fall back to the personality engine
(the user is unaware that a tool attempt occurred)

Layer 2: execute() fails → result=None → fall through to the personality engine

Layer 3: stdout is empty → leave user_message unchanged → the engine handles
it as a normal message
```

---

## 5. Known Trade-offs (Downstream Pollution)

Under v10 inject mode, `user_message` is reassigned before flowing into the following locations:

| Location | Content | Impact |
|---|---|---|
| `self.history` | Synthetic message stored in `history[-4:]` | ⚠️ Medium — subsequent Express light context includes injected text |
| `_evermemos_store_bg` | Synthetic message written to long-term memory | ⚠️ High — when retrieved, stdout may be treated as the user's speech |
| `_evermemos_search_bg` | Vector search query contains stdout | ⚠️ Low |
| `_last_action['user_input']` | Crystallization records synthetic text | ⚠️ Low |

**Phase D optimization**: Preserve `original_msg` and modify only the version passed to Actor, while using `original_msg` to write to history and EverMemOS. This requires changes inside the engine.

---

## 6. Memory Isolation

```text
chat.db (ChatLogStore)     ← Client-visible conversation history
task.db (TaskLogStore)     ← Isolated tool execution records
EverMemOS                  ← Long-term personality memory (v10: tool turns are also written, including injected data)
agent.history              ← Working memory (both tool and personality turns are written)
Hebbian                    ← Personality learning (v10: tool turns also trigger learning)
```

---

## 7. SKILL.md Authoring Guidelines

### Task Skill (`trigger: tool`)

The body of a Task Skill provides context for the LLM to generate shell commands. Follow these rules:

1. **Commands must include `--connect-timeout`** — prevents network operations from hanging indefinitely.
2. **Commands must include `|| echo "Error message"` fallback handling** — ensures stdout is never empty.
3. **Do not use nested `$(...)` subshells** — special characters can break URLs.
4. **For city names or parameters containing spaces in URLs, use `+` for encoding** — for example, `New+York`.

Example (weather SKILL):

```bash
# User-specified city
curl -s --connect-timeout 5 "wttr.in/Beijing?format=%l:+%c+%t+%h+%w" || echo "Weather lookup is temporarily unavailable"

# City not specified (automatic IP-based location)
curl -s --connect-timeout 5 "wttr.in/?format=%l:+%c+%t+%h+%w" || echo "Weather lookup is temporarily unavailable"
```

---

## 8. File Inventory

```text
agent/skills/
├── __init__.py          # Exports only SkillEngine
├── skill_engine.py      # Unified engine (L1/L2 + build_skill_declarations + execute)
├── sandbox_executor.py  # Shell command sandbox executor
└── task_log_store.py    # task.db isolated storage

providers/llm/
├── base.py              # ChatResponse.tool_calls + chat() tools
└── client.py            # Pass-through for tools/tool_choice

skills/weather/
└── SKILL.md             # trigger:tool + executor:sandbox

agent/chat_agent.py      # Guard clause + engine injection (_express_wrap removed)
```

---

## 9. Lessons Learned (10 Review Rounds, 24 Bugs, and v10 Iteration)

| Lesson | Representative bug |
|---|---|
| **Use `[system, user]` paired messages for every LLM call** | Bugs 1 and 4: Some providers reject system-only messages |
| **Tool paths must have exception fallbacks** | Bugs 6 and 9: An LLM failure must not interrupt the personality engine |
| **Always check boundary values** | Bugs 7 and 15: Empty commands and empty bodies must fail safely |
| **Normalize capitalization** | Bug 14: LLM returns `"Weather"` instead of `"weather"` |
| **SKILL commands must include their own fallback** | v10: When `curl` fails, stdout may be empty, causing data loss |
| **Do not use nested subshells for city detection** | v10: VPN city names containing spaces or quotes can break URLs |
| **Truncate stdout to prevent token explosion** | v10: A large stdout can inflate `user_message` beyond the token budget |

# Complete Guide to Creating OpenHer Personas

> This document records the complete process for creating a new persona, including the differences between Chinese and English, seed-design principles, vectorization workflows, and known pitfalls with their solutions. It is based on experience implementing Ember (English / INFP).

---

## I. Overview: The 4 Persona-Creation Stages

```
1. Define the persona (PERSONA.md)
2. Write the genesis seeds (genesis_xxx.json)
3. Vector-calibration setup (calibrate_genesis.py)
4. Validation testing (curl / UI)
```

Each stage contains details that require attention. Skipping any step may cause abnormal character behavior.

---

## II. Stage 1: Define the Persona (PERSONA.md)

Path: `persona/personas/<persona_id>/PERSONA.md`

### Required Fields

```yaml
name: Ember
age: 22
gender: female
mbti: INFP
lang: en          # ← Critical! Determines the language used throughout the prompt chain
tags: [quiet, observant, warm, poetic]
bio:
  en: >
    A 22-year-old bookstore clerk who writes poetry...
  zh: >
    22岁的书店店员...
```

### Differences Between Chinese and English Personas

| Field | Chinese Persona | English Persona |
|------|--------|---------|
| `lang` | `zh` | `en` |
| Actor template | `actor_single.md` | `actor_single_en.md` |
| Signal labels | `emoji_label` / `low_anchor` | `emoji_label_en` / `low_anchor_en` |
| Identity tag | `【角色】` | `[Character]` |
| Few-shot labels | `内心感受片段` / `基因` | `Inner feeling fragment` / `genesis` |
| Monologue tag | `【内心独白】` | `[Inner Monologue]` |
| Reply tag | `【最终回复】` | `[Final Reply]` |

> [!CAUTION]
> The `lang` field determines the language used by every downstream component. An incorrect value will cause the wrong signal anchors, template tags, and few-shot labels to be used, resulting in confused LLM output.

---

## III. Stage 2: Write the Genesis Seeds (genesis_xxx.json)

Path: After generation, calibrate them with `calibrate_genesis.py` and store them in the `genesis_seed` table in `openher.db`.

### Seed Structure

Each seed contains four core fields:

```json
{
  "user_input": "you're so cute haha",
  "monologue": "He said cute. Face is warm. I never know what to do with that.",
  "reply": "Oh… thanks.",
  "vector": [0, 0, 0, 0, 0, 0, 0, 0],
  "mass": 1.0
}
```

- `user_input`: The simulated text entered by the user, used for scenario classification and vectorization.
- `monologue`: The persona’s inner monologue; **this is injected into the Feel prompt as a few-shot reference**.
- `reply`: What the persona says aloud; used as a few-shot example in the single-pass Actor prompt and also influences crystallization.
- `vector`: **Initially set to `[0,0,0,0,0,0,0,0]`**. It is generated automatically by `calibrate_genesis.py`.
- `mass`: Fixed at `1.0`; genesis genes do not decay.

### Seed-Design Principles

> [!IMPORTANT]
> Seed quality directly determines the persona’s stylistic performance. The principles below summarize successful experience from Iris (Chinese / INFP).

#### 0. Prohibit Action and Mental-State Markers

The following must never appear in `monologue` or `reply`:

- `*顿了顿*`, `*sighs softly*` — text enclosed in asterisks, either `*` or `＊`
- `（沉默）`, `（轻轻笑）` — full-width parentheses
- `(pauses)`, `(laughs)` — half-width parentheses

Express inner states through the text itself rather than explanatory annotations. `calibrate_genesis.py` also removes these markers as a fallback before storing the data in the database.

#### 1. Monologues Must Be Fragmented

```
❌ "I feel really happy when he says that. It makes me feel warm inside
    and I don't know how to respond properly, but I want to say thank you."

✅ "He said cute. Face is warm. I never know what to do with that."
```

- Use short sentences and abrupt phrasing.
- Use stream of consciousness rather than complete paragraphs.
- Two or three short sentences are sufficient.

#### 2. Replies Must Be Extremely Brief

```
❌ "Thanks, that's really sweet of you to say! I appreciate it so much."

✅ "Oh… thanks."
```

- Use only 1–5 words.
- Include ellipses `…` or hesitation markers.
- Avoid advisory or expansive replies.

#### 3. Match the Core Traits of the MBTI Type

| MBTI | When complimented | When attacked | When confessed to |
|------|-------------------|---------------|-------------------|
| INFP | Shy, flustered | Withdraws, doubts themselves | Panics, needs time |
| ENTP | Returns the conversation, counters, banter | Debates and pushes back | Jokes about it, remains casual |
| INTJ | Accepts it calmly | Analyzes it calmly | Makes a rational assessment |

#### 4. Quantity and Scenario Coverage

**We recommend 35 or more seeds**, covering seven scenarios:

| Scenario | Example `user_input` | Recommended Quantity |
|----------|----------------------|----------------------|
| greeting | `"hi"`, `"hey"` | 2 |
| casual | `"what do you like to do"`, `"seen any movies"` | 8–10 |
| playful | `"you're cute"`, `"haha you're funny"` | 4–5 |
| intimate | `"I think I might like you"`, `"I trust you"` | 5–6 |
| distress | `"I've been feeling down"`, `"I can't sleep"` | 5–7 |
| rejection | `"I don't need you"`, `"just leave me alone"` | 4 |
| confrontation | `"you're so annoying"`, `"you're wrong"` | 5 |

> [!WARNING]
> Twenty seeds are insufficient. Inadequate scenario coverage may prevent KNN from finding suitable seeds in some scenarios, causing the LLM to fall back to default behavior.

#### 5. Include Persona-Specific Elements

Include unique details from the persona’s life:

```json
// Ember-specific details
"user_input": "do you have a cat",
"monologue": "Moth! Yes. He's asking about Moth. I could talk about her for hours.",
"reply": "Yeah… her name is Moth. She's a little gray thing."
```

These elements make the persona feel real rather than like a generic template.

---

## IV. Stage 3: Vector Calibration

### ❗ This is the easiest step to get wrong

Run:

```bash
cd /path/to/openher
source .venv/bin/activate
PYTHONPATH=. python3 scripts/calibrate_genesis.py <persona_id>
```

### Vector Space: It Must Be the Critic Context Space

> [!CAUTION]
> The vectors generated by `calibrate_genesis.py` must be in the **Critic context space** (8D: `conflict_level`, `user_emotion`, `user_engagement`, `user_vulnerability`, `topic_intimacy`, `conversation_depth`, `n[...]`).

During KNN retrieval, `_context_to_vec(context)` in `style_memory.py` obtains values from the Critic output. The KNN query therefore uses the context space. If the genesis vectors use the wrong space, KNN will retrieve entirely unrelated seeds.

**Correct implementation:**

```python
# In calibrate_genesis.py:
from engine.genome.style_memory import CONTEXT_KEYS
new_vector = [round(context.get(k, 0.0), 4) for k in CONTEXT_KEYS]
```

**Incorrect implementation that previously caused a bug:**

```python
# ❌ This generates vectors in signal space, which does not match the KNN query space!
signals = agent.compute_signals(context)
new_vector = [round(signals[s], 4) for s in SIGNALS]
```

### Scenario Classification: Keywords Used by `classify_input`

The `KEYWORD_MAP` in `calibrate_genesis.py` determines which scenario each seed belongs to and consequently determines its context vector.

Notes for English keywords:

- **Use short phrases**: `"down lately"` instead of `"feeling down"`; the latter may not match `"feeling **really** down"`
- **Ordering matters**: Python dictionaries preserve insertion order, and the first matching keyword determines the classification
- **Priority**: rejection > confrontation > distress > intimate > playful > casual > greeting
- **Default fallback**: `casual`; unmatched inputs are assigned to casual

### Common Bug Symptoms

| Symptom | Cause |
|---------|-------|
| KNN retrieves completely unrelated seeds | Vector-space mismatch: signal space versus context space |
| Nearly all seeds have almost identical vectors | `classify_input` lacks sufficient keywords, so most seeds are assigned to the same scenario |
| Seeds are missing for a specific scenario | Scenario keywords do not cover the relevant `user_input` values |

---

## V. Stage 4: Validation Testing

### Restart the Server

> [!IMPORTANT]
> The server **must be restarted** after modifying seeds. `uvicorn --reload` monitors changes to `.py` files but does not automatically reload database data.

```bash
kill -9 $(lsof -i :8800 -t 2>/dev/null) 2>/dev/null
sleep 2
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8800 --reload
```

### Test Script

```bash
# Use independent user_name values to avoid session contamination
i=0; for msg in \
  "you're so cute haha" \
  "I've been really stressed out lately" \
  "you're so annoying" \
  "I think I might like you" \
  "you're wrong about that"; do
  i=$((i+1))
  curl -s -X POST http://localhost:8800/api/chat \
    -H "Content-Type: application/json" \
    -d "{\"persona_id\":\"ember\",\"message\":\"$msg\",\"user_name\":\"test_$i\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('response',''))"
done
```

### Checklist

- [ ] **Language consistency**: All replies use the correct language, with no Chinese or English leakage where inappropriate.
- [ ] **KNN hits**: Retrieved seeds match the scenario; check the fragments in the Feel prompt.
- [ ] **Monologue style**: Fragmented and consistent with the MBTI profile.
- [ ] **Reply style**: Brief and consistent with the MBTI profile, not generic chatbot speech.
- [ ] **No Chinese characters in the prompt** for English personas: Scan the single-pass Actor prompt with a script.

### Debugging Method

Temporarily add dumps before and after Step 9 in `chat_agent.py`:

```python
# Temporary debugging; remove after verification
with open("/tmp/_dbg_single_prompt.txt", "w") as f:
    f.write(single_prompt)
# ... after the LLM call ...
with open("/tmp/_dbg_output.txt", "w") as f:
    f.write(single_response.content)
```

---

## VI. Known Pitfalls Summary

### Pitfall 1: Vector-Space Mismatch

- **Symptom**: KNN retrieves completely unrelated seeds.
- **Cause**: `calibrate_genesis.py` uses output from `compute_signals()` (signal space), while KNN queries use output from `_context_to_vec()` (Critic context space).
- **Fix**: Use `CONTEXT_KEYS` to extract values from `SCENARIO_CONTEXTS` as the vector.

### Pitfall 2: Chinese Tag Leakage

- **Symptom**: An English persona occasionally uses Chinese in replies.
- **Cause**: Tags such as `【角色】`, `【内心独白】`, and `【最终回复】` are not replaced in the English template.
- **Fix locations**:
  - `chat_agent.py` identity builder: replace `【角色】` with `[Character]`
  - `actor_feel_en.md`: replace `【内心独白】` with `[Inner Monologue]`
  - `actor_express_en.md`: replace `【最终回复】` with `[Final Reply]` and `【角色】` with `[Character]`

### Pitfall 3: Chinese Signal Anchors

- **Symptom**: Signal descriptions such as `0委婉→1直白` appear in English prompts.
- **Cause**: `load_signal_config` in `prompt_registry.py` parses only the default keys and discards keys with the `_en` suffix.
- **Fix**: Make `load_signal_config` pass through all `_en` keys.

### Pitfall 4: Insufficient English Keywords in `classify_input`

- **Symptom**: Many seeds are classified as `"greeting"` or `"casual"`, causing highly repetitive vectors.
- **Cause**: English keywords are too scarce or too long, so they do not match sentences containing intervening words.
- **Fix**: Use short-phrase keywords and arrange scenarios by priority.

### Pitfall 5: Express Style Drift

- **Symptom**: The monologue is appropriately shy and INFP-like, but the reply becomes an outgoing banter style.
- **Cause**: The Express prompt contains only identity and monologue information, with no stylistic constraint.
- **Fix**: Add the following to `actor_express_en.md`:

  ```
  The reply should directly mirror the tone and energy of the inner state.
  Do NOT add social pleasantries, topic changes, or enthusiasm
  that isn't in the inner state.
  Keep the reply brief.
  ```

### Pitfall 6: Session Contamination During Testing

- **Symptom**: Testing different personas with the same `user_name` causes their results to influence each other.
- **Cause**: Conversation history is stored by `(persona_id, user_id)`, and the session context may be shared.
- **Fix**: Use a unique `user_name` for each test.

### Pitfall 7: Server Caching

- **Symptom**: Behavior does not change after modifying `.md` templates or `.json` seeds.
- **Cause**: `uvicorn --reload` monitors only `.py` files; prompt templates and seeds may remain in memory caches.
- **Fix**: Restart the server or `touch` any `.py` file to trigger a reload.

---

## VII. Complete Operational Checklist

Complete steps for creating a new English persona:

```
□ 1. Create persona/personas/<id>/PERSONA.md
     - Set lang: en
     - Define MBTI, tags, bio, and engine_params

□ 2. Write the temporary genesis-seed JSON file
     - Include at least 35 seeds covering 7 scenarios
     - Keep monologues fragmented and replies extremely brief
     - Strictly prohibit *action* or (description) markers
     - Set every vector to [0,0,0,0,0,0,0,0]
     - Set every mass to 1.0

□ 3. Check keyword coverage in classify_input
     - Ensure every seed user_input is classified correctly
     - Add English keywords to KEYWORD_MAP if necessary

□ 4. Run calibrate_genesis.py to vectorize and store the data
     - PYTHONPATH=. python3 scripts/calibrate_genesis.py <id>
     - Check the output: verify the scenario assigned to each seed
     - Check vector ranges: vectors for different scenarios should be clearly distinct
     - After calibration, the data is automatically stored in the openher.db genesis_seed table

□ 5. Restart the server

□ 6. Run validation tests
     - Test 5 scenarios using independent user_name values
     - Check reply language, MBTI style, and seed hits
     - Scan prompts for Chinese-character leakage
```

---

*Last updated: March 9, 2026, based on complete implementation experience with Ember (English / INFP).*

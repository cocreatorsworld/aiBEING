# Qwen3-TTS-Instruct Voice Control Guide

Model: `qwen3-tts-instruct-flash-realtime` (DashScope WebSocket Realtime API)

---

## Three-Layer Control System

### Layer 1: `voice` — Base Voice (Choose “whose” voice)

A fixed system preset that determines the basic vocal characteristics. **Each persona is bound to one voice and keeps it unchanged.**

#### Female Voices

| voice | Name | Characteristics |
|:--|:--|:--|
| `Cherry` | 芊悦 | Cheerful, positive, approachable, and natural |
| `Serena` | 苏瑶 | Gentle |
| `Chelsie` | 千雪 | Anime-style virtual girlfriend |
| `Momo` | 茉兔 | Cute and playful |
| `Vivian` | 十三 | Sassy and adorably feisty |
| `Maia` | 四月 | Intellectual and gentle |
| `Mia` | 乖小妹 | Well-behaved and obedient |
| `Nini` | 邻家妹妹 | Soft and clingy |
| `Bella` | 萌宝 | Cute little girl |
| `Bunny` | 萌小姬 | Extremely cute |
| `Stella` | 少女阿月 | Sweet and distractibly youthful |
| `Seren` | 小婉 | Mild and soothing; suitable for sleep assistance |

#### Male Voices

| voice | Name | Characteristics |
|:--|:--|:--|
| `Ethan` | 晨煦 | Sunny, warm, and energetic |
| `Moon` | 月白 | Free-spirited and handsome |
| `Kai` | 凯 | A spa for the ears; magnetic voice |
| `Nofish` | 不吃鱼 | Designer; does not retroflex |

> See the [DashScope documentation](https://help.aliyun.com/zh/model-studio/qwen-tts-realtime) for the complete voice list.

---

### Layer 2: `instructions` — Instruction Control (Control “how it speaks”)

**Core capability.** The same voice can produce completely different results with different instructions.

#### Available Dimensions

| Dimension | Example Values |
|:--|:--|
| **Pitch** | Slightly high, slightly low, deep, crisp |
| **Speaking rate** | Slightly fast, slightly slow, medium |
| **Emotion** | Cheerful, composed, gentle, serious, lively, shy, calm, soothing |
| **Characteristics** | Magnetic, crisp, husky, mellow, sweet, resonant, powerful |
| **Context** | Like chatting with a close friend, like acting coy, like delivering a news broadcast |

#### Writing Principles

1. **Be specific:** `"deep voice"` is better than `"pleasant voice"`
2. **Use multiple dimensions:** `"speaking slightly fast, with a high pitch and a lively tone"` is better than `"high pitch"`
3. **Be objective:** Describe the vocal characteristics; do not say `"my favorite voice"`
4. **Be concise:** Every word should add meaning; avoid strings of synonyms

#### Examples

```text
# Different emotions using the same Cherry voice
Happy → "Speak quickly with an lively, cheerful tone, as if sharing good news"
Shy → "Speak slowly and softly, with shyness and hesitation"
Angry → "Speak loudly and quickly, with obvious dissatisfaction and a pout"
Acting coy → "Use a high pitch and a slightly slow pace, raise the final syllables, and sound coy and expectant"
Sad → "Speak slowly and with a low, heavy voice, conveying a sense of loss, as if about to cry"
Serious → "Enunciate clearly at a medium pace with a composed and earnest tone"
```

---

### Layer 3: `optimize_instructions=True`

When enabled, the model automatically rewrites instructions to make them more suitable for speech synthesis. It acts as a prompt-optimization layer.

It is recommended to keep this enabled.

---

## OpenHer Integration Strategy

```text
Base voice (voice, fixed for each persona)
    +
Dynamic instructions (instructions, generated in real time from the emotion for each conversation turn)
    =
Emotional, personalized speech
```

1. Bind a `voice` to each persona in the configuration.
2. After the engine outputs an emotional state, dynamically generate `instructions`.
3. When calling TTS, pass `voice` and `instructions`.

**No hard-coded emotion mapping table is needed** — natural language to natural language, allowing the LLM to directly describe how the response should be spoken.

---

## Analysis of the Official Examples

The following cases come from the official Qwen3-TTS demo and demonstrate three instruction-control modes.

### Mode A: Single-Attribute Control (Simple)

Use one sentence to control a single dimension. This is suitable for quickly switching emotions.

For example, with the **Ryan** voice and the same sentence, `"She said she would be here by noon."`:

| Instruction | Effect |
|:--|:--|
| `spoke with a very sad and tearful voice.` | Sad, tearful tone |
| `Very happy.` | Happy |
| `用特别愤怒的语气说` | Extremely angry tone |
| `请特别小声的悄悄说` | Whisper |
| `Speaking at an extremely slow pace` | Extremely slow pace |
| `音调低沉` | Deep pitch |

> **Key point:** Instructions can mix Chinese and English, and even a single dimension can create a significant effect.

### Mode B: Multi-Attribute Control (Rich) ⭐ Recommended for OpenHer

Use structured, multi-dimensional descriptions to create rich, personalized speech. **This is the mode OpenHer should use.**

For example, with the **Vivian** voice:

#### Example 1: Complete Personality Description (as a Persona Base Instruction)

```text
Gender: Female voice.
Pitch: Medium-high female range with highly varied intonation.
Speaking rate: Brisk, occasionally accelerating.
Volume: Normal conversational volume, with loud laughter.
Clarity: Clear enunciation and standard pronunciation.
Fluency: Fluent and natural expression.
Accent: Mandarin.
Vocal texture: Bright and slightly cheerful.
Emotion: Pleasant and friendly, with a bright smile in the voice.
Intonation: Upbeat and lively, especially at the end of questions.
Personality: Outgoing, cheerful, enthusiastic, and talkative.
```

> **Analysis:** This covers 11 dimensions and fully defines how a person speaks. It can serve as the persona’s **fixed base instruction**.

#### Example 2: Scene-Based Emotional Instruction (Dynamic Addition)

```text
In an extremely sad tone filled with obvious sobs, speak in a low voice and tell the story slowly.
Speak slowly, as though every word carries crushing pain.
Let the voice tremble and remain subdued, with soft but clear enunciation,
conveying sorrow and helplessness hidden deep in the heart.
```

> **Analysis:** This is a pure emotional instruction with strong imagery. It is suitable for converting the engine’s emotional state.

#### Example 3: Preserve the Vocal Identity While Adjusting the Style

```text
Maintain the vocal characteristics of a young woman, exhibiting a clear voice with a slight sense of urgency.
Begin at a steady pace and gradually speak faster during the narration.
Increase the volume as emotions fluctuate.
Raise the pitch at the end of sentences to emphasize a tone of advice or warning.
```

> **Analysis:** First anchor the voice so it remains unchanged, then describe the style changes. This is suitable for situations where a character needs to temporarily change tone without changing identity.

### Mode C: Cross-Language Use (Same Voice + Same Instructions → Different Languages)

The same Vivian voice and the same instructions can directly produce Korean, Japanese, Sichuanese, and other languages.

The model automatically identifies the language of the text and adjusts pronunciation while maintaining consistent vocal identity and emotion.

> **OpenHer implication:** An English persona does not need to switch voices; it can directly use the same voice to speak English.

---

## OpenHer Instruction Generation Strategy

Based on the preceding example analysis, **two-layer instruction stacking** is recommended:

```text
Final instructions = persona base instructions + current emotion instructions
```

### Persona Base Instructions (Fixed; Stored in the Persona Configuration)

One set for each persona, describing “how this person usually speaks”:

```yaml
# persona/personas/luna/persona.yaml
tts:
  voice: "Cherry"
  base_instructions: |
    Pitch: Medium-high female range with noticeable intonation variation.
    Speaking rate: Brisk and faster when excited.
    Vocal texture: Bright and sweet, with a youthful quality.
    Personality: Outgoing, lively, and energetic.
```

### Current Emotion Instruction (Dynamic; Generated from the Engine’s Emotion Analysis)

Generated for every conversation turn based on the emotional state:

```text
# Engine output: emotion=excited
→ "Speak with strong excitement, at a slightly fast pace, with a rising voice, as if discovering something fun"
```

### Combine Before Passing to TTS

```text
instructions = base_instructions + "\nCurrent emotion: " + emotion_instructions
```

---

## API Notes

| Parameter | Value |
|:--|:--|
| Model | `qwen3-tts-instruct-flash-realtime` |
| Protocol | WebSocket (`wss://dashscope.aliyuncs.com/api-ws/v1/realtime`) |
| SDK | `dashscope.audio.qwen_tts_realtime.QwenTtsRealtime` |
| Audio format | PCM, 24 kHz, mono, 16-bit → save as WAV |
| Instruction length limit | ≤ 1600 tokens |
| Instruction language | Chinese and English only |
| Rate limit | 180 RPM |
| Price | ¥1 per 10,000 characters |

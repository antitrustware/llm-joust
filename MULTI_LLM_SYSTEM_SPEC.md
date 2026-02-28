# Multi-LLM Fan-Out & Evaluation System — Build Spec for Claude Code

## What This Document Is

This is a complete specification for Claude Code to architect, build, and configure a production-ready system that sends a single prompt to four LLM APIs in parallel, collects their responses, then has each model evaluate all four responses and declare a winner. The entire system should live in a single dedicated project folder that is self-contained, secure, and runnable from the terminal via Claude Code.

**How to use:** Open Claude Code, navigate to an empty directory (e.g. `~/multi-llm/`), and paste: `Read MULTI_LLM_SYSTEM_SPEC.md and build the entire system according to the spec`. Then add your API keys to `.env` when prompted.

---

## System Overview

### The Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│  ROUND 1 — Fan-Out                                                  │
│                                                                     │
│  User Prompt ──┬──► Claude  (Anthropic API)  ──► Response A         │
│                ├──► GPT-5.2 (OpenAI API)     ──► Response B         │
│                ├──► Gemini  (Google AI API)   ──► Response C         │
│                └──► Grok    (xAI API)        ──► Response D         │
│                                                                     │
│  ROUND 2 — Evaluation                                               │
│                                                                     │
│  All 4 responses ──┬──► Claude judges  ──► Ranking + Winner         │
│                    ├──► GPT-5.2 judges ──► Ranking + Winner         │
│                    ├──► Gemini judges  ──► Ranking + Winner         │
│                    └──► Grok judges    ──► Ranking + Winner         │
│                                                                     │
│  ROUND 3 — Tally                                                    │
│                                                                     │
│  Aggregate all 4 judgments ──► Points + Votes ──► Overall Winner    │
└─────────────────────────────────────────────────────────────────────┘
```

### Models & Endpoints

| Name    | Provider  | Model String                     | Base URL                    | API Key Env Var     | Notes |
|---------|-----------|----------------------------------|-----------------------------|---------------------|-------|
| Claude  | Anthropic | `claude-opus-4-6`               | `https://api.anthropic.com` | `ANTHROPIC_API_KEY` | Adaptive thinking enabled |
| GPT-5.2 | OpenAI   | `gpt-5.2`                        | `https://api.openai.com`    | `OPENAI_API_KEY`    | Built-in reasoning |
| Gemini  | Google    | `gemini-2.5-flash`               | Google AI SDK (no base URL) | `GOOGLE_API_KEY`    | Free tier available |
| Grok    | xAI       | `grok-4-1-fast-non-reasoning`    | `https://api.x.ai/v1`      | `XAI_API_KEY`       | OpenAI-compatible SDK |

**Important API compatibility notes:**
- **Grok** uses an OpenAI-compatible API, so use the OpenAI SDK with a custom `base_url`.
- **OpenAI (GPT-5.2+) and Grok** require `max_completion_tokens` instead of `max_tokens`.
- **Claude (Opus 4.6)** uses adaptive thinking (`thinking.type=adaptive`). The model decides when and how much to think. When thinking is enabled, `temperature` must be set to `1`. Set `max_tokens` high enough to accommodate thinking + response. The response contains thinking blocks and text blocks — extract the text block for the final answer.
- **Gemini** still uses `max_output_tokens`.

---

## Project Folder Structure

Create this exact structure inside a dedicated project directory (e.g. `~/multi-llm/`):

```
multi-llm/
├── .env                      # API keys (gitignored, never committed)
├── .env.example              # Template showing required keys (safe to commit)
├── .gitignore                # Ignores .env, __pycache__, logs/, results/
├── README.md                 # Usage instructions (generated from this spec)
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Optional: project metadata + tool config
│
├── src/
│   ├── __init__.py
│   ├── config.py             # Loads .env, defines model configs, constants
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract base class for model callers
│   │   ├── claude.py         # Anthropic API caller
│   │   ├── openai_caller.py  # OpenAI API caller (GPT-5.2)
│   │   ├── gemini.py         # Google Gemini API caller
│   │   └── grok.py           # xAI Grok API caller (OpenAI-compatible)
│   │
│   ├── pipeline.py           # Orchestrates fan-out, evaluation, and tallying
│   ├── judge.py              # Builds judge prompts, parses judge responses
│   ├── display.py            # Terminal output formatting (colors, tables)
│   └── utils.py              # Shared helpers (retry logic, timeout, logging)
│
├── cli.py                    # Main entry point — CLI with argparse
│
├── results/                  # Stores JSON output of each run (auto-created)
│   └── .gitkeep
│
├── logs/                     # Stores debug logs (auto-created)
│   └── .gitkeep
│
├── prompts/                  # Saved prompt files for --file mode
│   └── example.txt
│
└── CLAUDE.md                 # Claude Code project instructions (see below)
```

---

## CLAUDE.md — Claude Code Project Instructions

Create a `CLAUDE.md` file in the project root with the following content. This tells Claude Code how to work within this project:

```markdown
# Project: Multi-LLM Fan-Out & Evaluation System

## What This Project Does
Sends a prompt to 4 LLM APIs (Claude Opus 4.6, GPT-5.2, Gemini, Grok) in parallel, collects responses, then has each model judge all responses and pick a winner.

## Models
- **Claude**: `claude-opus-4-6` with adaptive thinking
- **GPT-5.2**: `gpt-5.2` (uses `max_completion_tokens`, not `max_tokens`)
- **Gemini**: `gemini-2.5-flash`
- **Grok**: `grok-4-1-fast-non-reasoning` (OpenAI-compatible SDK, uses `max_completion_tokens`)

## Key Commands
- Run a prompt: `python cli.py "Your prompt here"`
- Interactive mode: `python cli.py -i`
- From file: `python cli.py -f prompts/example.txt`
- JSON output: `python cli.py --json "prompt"`

## Architecture
- `src/config.py` — loads .env, model configs
- `src/models/` — one module per LLM provider
- `src/pipeline.py` — orchestrates the 3-round pipeline
- `src/judge.py` — evaluation prompt construction + response parsing
- `cli.py` — entry point

## Environment
- Python 3.11+
- API keys stored in `.env` (never commit this file)
- All dependencies in `requirements.txt`

## Rules
- Always use async/await for API calls
- All API calls must have timeout handling (120s default)
- Never hardcode API keys anywhere
- Results are saved to `results/` as JSON after each run
- Gracefully skip models with missing API keys
- Claude uses adaptive thinking (temperature must be 1, response has thinking + text blocks)
- OpenAI and Grok use `max_completion_tokens` (not `max_tokens`)
```

---

## Detailed Implementation Requirements

### 1. Environment & Credentials (`config.py`)

- Use `python-dotenv` to load from `.env` file in project root.
- Define a dataclass or dict for each model's config: name, model string, API key env var, base URL, caller function.
- Validate on startup: warn (don't crash) if a key is missing. Skip that model gracefully.
- Expose configurable constants: `TIMEOUT = 120`, `TEMPERATURE = 0.7`, `JUDGE_TEMPERATURE = 0.3`, `MAX_TOKENS = 4096`.

The `.env` file format:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
XAI_API_KEY=xai-...
```

The `.env.example` file (safe to commit):

```
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=
XAI_API_KEY=
```

### 2. Model Callers (`src/models/`)

Each model caller should:

- Be async (`async def call(prompt, system="", temperature=0.7) -> str`).
- Accept `prompt` (str), optional `system` prompt (str), and `temperature` (float).
- Return the response text as a string.
- Raise exceptions on failure (caught by the pipeline layer).

**Claude (`claude.py`):**
```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=api_key)  # pass key from config
response = await client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16384,  # high enough for thinking + response
    temperature=1,  # must be 1 when thinking is enabled
    thinking={
        "type": "adaptive",  # model decides when/how much to think
    },
    system=system,  # pass as top-level kwarg, not in messages
    messages=[{"role": "user", "content": prompt}],
)
# Response contains thinking blocks + text blocks; extract the text
for block in response.content:
    if block.type == "text":
        return block.text
```

**GPT-5.2 (`openai_caller.py`):**
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=api_key)  # pass key from config
messages = []
if system:
    messages.append({"role": "system", "content": system})
messages.append({"role": "user", "content": prompt})

response = await client.chat.completions.create(
    model="gpt-5.2",
    max_completion_tokens=4096,  # NOT max_tokens — required for GPT-5.2+
    temperature=temperature,
    messages=messages,
)
return response.choices[0].message.content
```

**Gemini (`gemini.py`):**
```python
from google import genai
from google.genai.types import GenerateContentConfig

client = genai.Client(api_key=api_key)  # pass key from config
config = GenerateContentConfig(temperature=temperature, max_output_tokens=4096)
if system:
    config.system_instruction = system

# google-genai client is synchronous, wrap in asyncio.to_thread
response = await asyncio.to_thread(
    client.models.generate_content,
    model="gemini-2.5-flash",
    contents=prompt,
    config=config,
)
return response.text
```

**Grok (`grok.py`):**
```python
from openai import AsyncOpenAI

# Grok uses OpenAI-compatible API with custom base_url
client = AsyncOpenAI(
    api_key=api_key,  # pass key from config
    base_url="https://api.x.ai/v1",
)
# Same pattern as GPT-5.2 but with model="grok-4-1-fast-non-reasoning"
# Also uses max_completion_tokens (not max_tokens)
```

### 3. Pipeline (`pipeline.py`)

**Round 1 — Fan-Out:**
- Send the user's prompt to all available models in parallel using `asyncio.gather()`.
- Wrap each call in `asyncio.wait_for()` with the configured timeout.
- Catch all exceptions per-model. Return a `ModelResponse` dataclass per model containing: `model_name`, `response`, `latency`, `error` (None if success).
- Track wall-clock latency for each model.

**Round 2 — Evaluation:**
- Build a judge prompt that includes the original user prompt and all successful responses, labeled by model name.
- Send the judge prompt to each model that responded successfully in Round 1 (a model that failed in Round 1 should not judge).
- Use a lower temperature for judging (`JUDGE_TEMPERATURE = 0.3`).
- Use a system prompt instructing the model to be an impartial judge evaluating on: accuracy, completeness, clarity, usefulness, and reasoning quality.
- Instruct each judge to return JSON: `{"rankings": [...], "winner": "...", "reasoning": "..."}`.
- Parse JSON from the response, handling markdown code fences (`` ```json ``` ``) gracefully.

**Round 3 — Tally:**
- Count first-place votes per model.
- Assign points based on ranking position (4 pts for 1st, 3 for 2nd, 2 for 3rd, 1 for 4th).
- Determine overall winner by total points (break ties by first-place vote count).
- Return a structured result dict.

### 4. Judge Prompt Template (`judge.py`)

```
I asked {n} AI models the following question:

<original_prompt>
{user_prompt}
</original_prompt>

Here are their responses:

--- Claude ---
{claude_response}

--- GPT-5.2 ---
{gpt52_response}

--- Gemini ---
{gemini_response}

--- Grok ---
{grok_response}

Please evaluate all responses and:
1. Rank them from best to worst.
2. Pick a single winner.
3. Explain your reasoning in 2-3 sentences.

Respond in this exact JSON format and nothing else:
{
    "rankings": ["Best Model", "Second", "Third", "Fourth"],
    "winner": "Best Model",
    "reasoning": "Your explanation here."
}
```

### 5. CLI (`cli.py`)

Support these modes:

```bash
# Direct prompt
python cli.py "What is the best programming language for beginners?"

# Interactive mode (multi-line input, double-Enter to send)
python cli.py -i
python cli.py --interactive

# Read prompt from file
python cli.py -f prompts/my_question.txt
python cli.py --file prompts/my_question.txt

# Output as JSON (for piping / scripting)
python cli.py --json "Your prompt"

# Specify which models to use (subset)
python cli.py --models claude,gpt52 "Your prompt"

# Skip the evaluation round (just get raw responses)
python cli.py --no-eval "Your prompt"

# Verbose debug logging
python cli.py -v "Your prompt"
```

### 6. Results Storage (`results/`)

After each run, automatically save the full result as a JSON file:

```
results/2026-02-28_143052_abc123.json
```

The JSON should contain:
- `timestamp` (ISO format)
- `prompt` (the original user prompt)
- `responses` (array of model name, response text, latency, error)
- `judgments` (array of judge name, winner, rankings, reasoning)
- `final_winner`
- `points_breakdown`
- `votes_breakdown`

### 7. Terminal Display (`display.py`)

Use ANSI color codes for readable terminal output:

- **Round 1:** Show each model's response as a truncated preview (first 500 chars) with latency.
- **Round 2:** Show each judge's pick, ranking, and reasoning.
- **Round 3:** Show the final winner with a points bar chart and vote counts.
- Use bold, cyan, green, yellow, and dim formatting.
- Keep it clean — don't over-decorate.

### 8. Error Handling & Resilience

- **Missing API keys:** Warn and skip that model. Continue with remaining models.
- **API timeouts:** 120s default. Return error response, don't crash.
- **Rate limits:** Implement exponential backoff with 3 retries per model.
- **JSON parse failures in judging:** If a judge returns invalid JSON, attempt to extract the winner name from raw text. Mark judgment as degraded.
- **Minimum models:** Require at least 2 successful responses to proceed to evaluation. If fewer, display what you have and skip judging.

---

## Dependencies

### `requirements.txt`

```
anthropic>=0.40.0
openai>=1.50.0
google-genai>=1.0.0
python-dotenv>=1.0.0
```

### System Requirements

- Python 3.11 or higher (for native `asyncio.TaskGroup` and `str | None` syntax)
- No external services beyond the 4 LLM APIs

---

## API Key Setup Instructions

Include these in the generated README.md:

### Getting Your API Keys

These are **separate from your chat subscriptions** (Claude Max, ChatGPT Pro, etc.). API access is billed independently.

1. **Anthropic (Claude)**
   - Go to: https://console.anthropic.com/
   - Create an account or sign in
   - Navigate to API Keys → Create Key
   - Free tier gives $5 in credits to start
   - Set as: `ANTHROPIC_API_KEY=sk-ant-...`

2. **OpenAI (GPT-5.2)**
   - Go to: https://platform.openai.com/api-keys
   - Create an account or sign in
   - Add payment method (pay-as-you-go)
   - Create a new secret key
   - Set as: `OPENAI_API_KEY=sk-...`

3. **Google (Gemini)**
   - Go to: https://aistudio.google.com/apikey
   - Sign in with Google account
   - Create an API key (generous free tier available)
   - Set as: `GOOGLE_API_KEY=...`

4. **xAI (Grok)**
   - Go to: https://console.x.ai/
   - Create an account and add credits ($5 minimum)
   - Create an API key
   - Set as: `XAI_API_KEY=xai-...`

### Approximate Cost Per Run

Each run makes ~8 API calls (4 generation + 4 judging). Approximate costs:

| Model   | Generation  | Judging     | ~Total per run |
|---------|-------------|-------------|----------------|
| Claude  | $0.02–0.08  | $0.03–0.10  | ~$0.15         |
| GPT-5.2 | $0.01–0.05  | $0.02–0.08  | ~$0.10         |
| Gemini  | $0.01–0.03  | $0.01–0.05  | ~$0.06         |
| Grok    | $0.01–0.03  | $0.01–0.03  | ~$0.04         |

**Total per run: ~$0.20–$0.35** depending on prompt and response length. Claude (Opus 4.6) is the most expensive model at $5/$25 per M tokens, but also the most capable.

---

## Optional Enhancements (Build If Time Permits)

These are nice-to-haves. Implement only after the core system works:

1. **Configurable model list via `.env`:** Let users swap model versions (e.g., `CLAUDE_MODEL=claude-opus-4-6`) without editing code.
2. **Streaming output:** Stream Round 1 responses to terminal as they arrive instead of waiting for all to complete.
3. **History browser:** A CLI command like `python cli.py --history` that lists past runs from `results/` and lets you view one.
4. **Custom judge criteria:** Allow a `--criteria` flag to override the default evaluation rubric (e.g., `--criteria "focus on code quality and correctness"`).
5. **Consensus synthesis:** After tallying, send the winning response + all judge reasoning back to one model to produce a final synthesized answer.

---

## Summary of What Claude Code Should Build

1. Create the project folder structure exactly as specified above.
2. Implement all source files in `src/` with proper async patterns.
3. Create `cli.py` as the main entry point with all specified flags.
4. Generate `.env.example`, `.gitignore`, `requirements.txt`, and `README.md`.
5. Create the `CLAUDE.md` project instructions file.
6. Ensure the system works end-to-end with `python cli.py "test prompt"`.
7. Handle all error cases gracefully (missing keys, timeouts, parse failures).
8. Save results as JSON after each run.
9. Install dependencies via `pip install -r requirements.txt`.
10. Prompt the user to add their API keys to `.env` before the first run.

The system should be immediately runnable after setting API keys in `.env`.

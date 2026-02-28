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

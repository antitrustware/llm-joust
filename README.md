# Multi-LLM Fan-Out & Evaluation System

Send a single prompt to four LLM APIs in parallel, collect their responses, then have each model evaluate all responses and declare a winner.

## Models

| Model   | Provider  | ID                              | Feature |
|---------|-----------|---------------------------------|---------|
| Claude  | Anthropic | `claude-opus-4-6`               | Adaptive thinking |
| GPT-5.2 | OpenAI    | `gpt-5.2`                       | Built-in reasoning |
| Gemini  | Google    | `gemini-2.5-flash`              | Fast, free tier available |
| Grok    | xAI       | `grok-4-1-fast-non-reasoning`   | Great price/performance |

## Pipeline

```
Round 1 — Fan-Out:    Prompt → 4 models in parallel → 4 responses
Round 2 — Evaluation: All responses → each model judges → 4 rankings
Round 3 — Tally:      Aggregate judgments → points + votes → overall winner
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env` with your API keys. The system will gracefully skip any model whose key is missing.

### 3. Run

```bash
python cli.py "What is the best programming language for beginners?"
```

## Usage

```bash
# Direct prompt
python cli.py "Your prompt here"

# Interactive mode (multi-line input, double-Enter to send)
python cli.py -i

# Read prompt from file
python cli.py -f prompts/example.txt

# Output as JSON (for piping/scripting)
python cli.py --json "Your prompt"

# Use specific models only
python cli.py --models claude,gpt52 "Your prompt"

# Skip evaluation (just get raw responses)
python cli.py --no-eval "Your prompt"

# Verbose debug logging
python cli.py -v "Your prompt"
```

## Getting Your API Keys

These are **separate from your chat subscriptions** (Claude Max, ChatGPT Pro, etc.). API access is billed independently.

### Anthropic (Claude)
- Go to: https://console.anthropic.com/
- Create an account or sign in
- Navigate to API Keys → Create Key
- Free tier gives $5 in credits to start
- Set as: `ANTHROPIC_API_KEY=sk-ant-...`

### OpenAI (GPT-5.2)
- Go to: https://platform.openai.com/api-keys
- Create an account or sign in
- Add payment method (pay-as-you-go)
- Create a new secret key
- Set as: `OPENAI_API_KEY=sk-...`

### Google (Gemini)
- Go to: https://aistudio.google.com/apikey
- Sign in with Google account
- Create an API key (generous free tier available)
- Set as: `GOOGLE_API_KEY=...`

### xAI (Grok)
- Go to: https://console.x.ai/
- Create an account and add credits ($5 minimum)
- Create an API key
- Set as: `XAI_API_KEY=xai-...`

## Approximate Cost Per Run

Each run makes ~8 API calls (4 generation + 4 judging):

| Model   | Generation  | Judging     | ~Total per run |
|---------|-------------|-------------|----------------|
| Claude  | $0.02–0.08  | $0.03–0.10  | ~$0.15         |
| GPT-5.2 | $0.01–0.05  | $0.02–0.08  | ~$0.10         |
| Gemini  | $0.01–0.03  | $0.01–0.05  | ~$0.06         |
| Grok    | $0.01–0.03  | $0.01–0.03  | ~$0.04         |

**Total per run: ~$0.20–$0.35** depending on prompt and response length.

## Project Structure

```
multi-llm/
├── cli.py              # Main entry point
├── src/
│   ├── config.py       # Environment & model configuration
│   ├── models/         # One module per LLM provider
│   │   ├── claude.py   # Opus 4.6 with adaptive thinking
│   │   ├── openai_caller.py  # GPT-5.2
│   │   ├── gemini.py   # Gemini 2.5 Flash
│   │   └── grok.py     # Grok 4.1 Fast
│   ├── pipeline.py     # 3-round orchestration
│   ├── judge.py        # Judge prompt construction & parsing
│   ├── display.py      # Terminal formatting
│   └── utils.py        # Retry logic, timeout, logging
├── results/            # JSON output of each run
├── logs/               # Debug logs
└── prompts/            # Saved prompt files
```

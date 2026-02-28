"""Orchestrates the 3-round pipeline: fan-out, evaluation, and tallying."""

import asyncio
import logging
import time
from dataclasses import dataclass, field

from .config import ModelConfig, TIMEOUT, TEMPERATURE, JUDGE_TEMPERATURE, get_available_models
from .models import call_claude, call_gpt4o, call_gemini, call_grok
from .judge import JUDGE_SYSTEM_PROMPT, build_judge_prompt, parse_judge_response
from .utils import retry_with_backoff, with_timeout

logger = logging.getLogger(__name__)

# Map model names to their call functions
CALLERS = {
    "Claude": call_claude,
    "GPT-5.2": call_gpt4o,
    "Gemini": call_gemini,
    "Grok": call_grok,
}


@dataclass
class ModelResponse:
    model_name: str
    response: str = ""
    latency: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "response": self.response,
            "latency": round(self.latency, 2),
            "error": self.error,
        }


@dataclass
class JudgmentResult:
    judge_name: str
    winner: str = ""
    rankings: list[str] = field(default_factory=list)
    reasoning: str = ""
    degraded: bool = False

    def to_dict(self) -> dict:
        return {
            "judge_name": self.judge_name,
            "winner": self.winner,
            "rankings": self.rankings,
            "reasoning": self.reasoning,
            "degraded": self.degraded,
        }


@dataclass
class PipelineResult:
    prompt: str
    responses: list[ModelResponse] = field(default_factory=list)
    judgments: list[JudgmentResult] = field(default_factory=list)
    final_winner: str = ""
    points: dict[str, int] = field(default_factory=dict)
    votes: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "responses": [r.to_dict() for r in self.responses],
            "judgments": [j.to_dict() for j in self.judgments],
            "final_winner": self.final_winner,
            "points_breakdown": self.points,
            "votes_breakdown": self.votes,
        }


async def _call_model(
    name: str, prompt: str, system: str = "", temperature: float = TEMPERATURE
) -> ModelResponse:
    """Call a single model with retry and timeout."""
    caller = CALLERS.get(name)
    if caller is None:
        return ModelResponse(model_name=name, error=f"No caller registered for {name}")

    start = time.monotonic()
    try:
        text = await with_timeout(
            retry_with_backoff(caller, prompt, system=system, temperature=temperature),
            timeout=TIMEOUT,
        )
        elapsed = time.monotonic() - start
        return ModelResponse(model_name=name, response=text, latency=elapsed)
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start
        logger.error("%s timed out after %.1fs", name, elapsed)
        return ModelResponse(model_name=name, latency=elapsed, error="Timeout")
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("%s failed: %s", name, e)
        return ModelResponse(model_name=name, latency=elapsed, error=str(e))


async def round1_fanout(
    prompt: str, models: dict[str, ModelConfig] | None = None
) -> list[ModelResponse]:
    """Round 1: Send prompt to all available models in parallel."""
    if models is None:
        models = get_available_models()

    tasks = [_call_model(name, prompt) for name in models]
    results = await asyncio.gather(*tasks)
    return list(results)


async def round2_evaluate(
    prompt: str, responses: list[ModelResponse]
) -> list[JudgmentResult]:
    """Round 2: Have each successful model judge all responses."""
    # Only models that responded successfully can judge
    successful = {r.model_name: r.response for r in responses if r.error is None}

    if len(successful) < 2:
        logger.warning("Fewer than 2 successful responses — skipping evaluation.")
        return []

    judge_prompt = build_judge_prompt(prompt, successful)
    valid_models = list(successful.keys())

    async def _judge(name: str) -> JudgmentResult:
        resp = await _call_model(
            name, judge_prompt, system=JUDGE_SYSTEM_PROMPT, temperature=JUDGE_TEMPERATURE
        )
        if resp.error:
            return JudgmentResult(judge_name=name, reasoning=f"Error: {resp.error}")

        parsed = parse_judge_response(resp.response, valid_models)
        return JudgmentResult(
            judge_name=name,
            winner=parsed["winner"],
            rankings=parsed["rankings"],
            reasoning=parsed["reasoning"],
            degraded=parsed["degraded"],
        )

    tasks = [_judge(name) for name in successful]
    results = await asyncio.gather(*tasks)
    return list(results)


def round3_tally(
    responses: list[ModelResponse], judgments: list[JudgmentResult]
) -> tuple[str, dict[str, int], dict[str, int]]:
    """Round 3: Aggregate judgments into points and votes.

    Returns (winner, points_dict, votes_dict).
    """
    successful_names = [r.model_name for r in responses if r.error is None]
    points: dict[str, int] = {name: 0 for name in successful_names}
    votes: dict[str, int] = {name: 0 for name in successful_names}

    n_models = len(successful_names)
    # Points: n for 1st, n-1 for 2nd, etc.
    point_values = list(range(n_models, 0, -1))

    for j in judgments:
        # Count first-place votes
        if j.winner and j.winner in votes:
            votes[j.winner] += 1

        # Award points based on ranking
        for i, name in enumerate(j.rankings):
            if name in points and i < len(point_values):
                points[name] += point_values[i]

    # Determine winner: highest points, break ties by votes
    if not points:
        return "", points, votes

    winner = max(
        points.keys(),
        key=lambda name: (points[name], votes.get(name, 0)),
    )

    return winner, points, votes


async def run_pipeline(
    prompt: str,
    model_subset: list[str] | None = None,
    skip_eval: bool = False,
) -> PipelineResult:
    """Run the full 3-round pipeline."""
    models = get_available_models(model_subset)

    if not models:
        result = PipelineResult(prompt=prompt)
        logger.error("No models available. Check your API keys.")
        return result

    # Round 1
    responses = await round1_fanout(prompt, models)

    result = PipelineResult(prompt=prompt, responses=responses)

    successful_count = sum(1 for r in responses if r.error is None)

    if skip_eval or successful_count < 2:
        return result

    # Round 2
    judgments = await round2_evaluate(prompt, responses)
    result.judgments = judgments

    # Round 3
    winner, points, votes = round3_tally(responses, judgments)
    result.final_winner = winner
    result.points = points
    result.votes = votes

    return result

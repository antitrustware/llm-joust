"""Builds judge prompts and parses judge responses."""

import json
import re
import logging

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = (
    "You are an impartial AI response evaluator. Evaluate responses based on: "
    "accuracy, completeness, clarity, usefulness, and reasoning quality. "
    "Be fair and objective. Do not favor any particular AI model. "
    "Respond ONLY with the requested JSON format."
)


def build_judge_prompt(
    user_prompt: str, responses: dict[str, str]
) -> str:
    """Build the evaluation prompt for judges.

    Args:
        user_prompt: The original user prompt.
        responses: Dict mapping model name to response text.
    """
    n = len(responses)
    parts = [
        f"I asked {n} AI models the following question:\n",
        "<original_prompt>",
        user_prompt,
        "</original_prompt>\n",
        "Here are their responses:\n",
    ]

    for name, text in responses.items():
        parts.append(f"--- {name} ---")
        parts.append(text)
        parts.append("")

    model_names = list(responses.keys())
    example_rankings = json.dumps(model_names)

    parts.append("Please evaluate all responses and:")
    parts.append("1. Rank them from best to worst.")
    parts.append("2. Pick a single winner.")
    parts.append("3. Explain your reasoning in 2-3 sentences.")
    parts.append("")
    parts.append("Respond in this exact JSON format and nothing else:")
    parts.append("{")
    parts.append(f'    "rankings": {example_rankings},')
    parts.append(f'    "winner": "{model_names[0]}",')
    parts.append('    "reasoning": "Your explanation here."')
    parts.append("}")

    return "\n".join(parts)


def parse_judge_response(raw: str, valid_models: list[str]) -> dict:
    """Parse a judge's JSON response, handling markdown fences.

    Returns a dict with keys: rankings, winner, reasoning, degraded.
    """
    # Strip markdown code fences
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        data = json.loads(cleaned)
        return {
            "rankings": data.get("rankings", []),
            "winner": data.get("winner", ""),
            "reasoning": data.get("reasoning", ""),
            "degraded": False,
        }
    except json.JSONDecodeError:
        logger.warning("Failed to parse judge JSON, attempting fallback extraction.")

    # Fallback: try to find winner from raw text
    winner = _extract_winner_fallback(raw, valid_models)
    return {
        "rankings": [],
        "winner": winner,
        "reasoning": "(JSON parse failed — winner extracted from raw text)",
        "degraded": True,
    }


def _extract_winner_fallback(text: str, valid_models: list[str]) -> str:
    """Attempt to find a model name in the raw text as a fallback."""
    text_lower = text.lower()
    for model in valid_models:
        if model.lower() in text_lower:
            return model
    return ""

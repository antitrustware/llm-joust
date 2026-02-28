"""Builds judge prompts, auto-detects evaluation criteria, and parses judge responses."""

import json
import re
import logging

logger = logging.getLogger(__name__)

# --- Criteria Presets ---

CRITERIA_PRESETS: dict[str, dict] = {
    "code": {
        "label": "Code Quality",
        "criteria": "correctness, efficiency, readability, best practices, and error handling",
        "keywords": [
            "code", "function", "class", "implement", "bug", "debug", "refactor",
            "algorithm", "api", "script", "program", "syntax", "compile", "runtime",
            "python", "javascript", "typescript", "rust", "java", "sql", "html", "css",
            "react", "django", "flask", "node", "git", "docker", "regex", "database",
            "def ", "import ", "print(", "console.log", "return ", "for loop", "while loop",
        ],
    },
    "creative": {
        "label": "Creative Writing",
        "criteria": "originality, style, engagement, emotional impact, and literary craft",
        "keywords": [
            "write a story", "write a poem", "write a short", "write a song",
            "creative", "fiction", "narrative", "poem", "poetry", "story",
            "character", "dialogue", "plot", "scene", "metaphor", "haiku", "sonnet",
            "short story", "essay", "blog post", "write me", "compose", "draft",
            "tone", "voice", "rewrite", "storytelling", "limerick", "fairy tale",
        ],
    },
    "factual": {
        "label": "Factual Accuracy",
        "criteria": "accuracy, sourcing, depth, objectivity, and comprehensiveness",
        "keywords": [
            "what is", "what are", "what was", "who is", "who was", "when did",
            "when was", "where is", "where was", "how does", "how do",
            "explain", "define", "history of", "tell me about", "capital of",
            "difference between", "compare", "facts", "true", "science", "research",
            "evidence", "study", "data", "statistics", "according to", "founded",
        ],
    },
    "reasoning": {
        "label": "Analytical Reasoning",
        "criteria": "logical validity, evidence quality, consideration of counterarguments, depth of analysis, and conclusion strength",
        "keywords": [
            "why", "argue", "argument", "debate", "pros and cons", "trade-off",
            "should i", "should we", "best approach", "analyze", "analysis",
            "evaluate", "assess", "critical", "logic", "reasoning", "think through",
            "implications", "consequences", "cause and effect", "opinion",
            "what would happen", "hypothetical", "thought experiment",
        ],
    },
    "instructional": {
        "label": "Instructional Clarity",
        "criteria": "clarity, step-by-step structure, actionability, completeness, and accessibility",
        "keywords": [
            "how to", "tutorial", "guide", "step by step", "steps to", "instructions",
            "teach me", "learn", "walkthrough", "setup", "install", "configure",
            "build", "create a", "make a", "recipe", "plan", "checklist",
        ],
    },
    "math": {
        "label": "Mathematical Rigor",
        "criteria": "correctness, methodology, clarity of explanation, mathematical notation, and proof quality",
        "keywords": [
            "solve", "equation", "calculate", "math", "formula", "proof", "theorem",
            "integral", "derivative", "probability", "statistics", "algebra",
            "geometry", "calculus", "matrix", "vector", "polynomial",
            "sum of", "product of", "find x", "find the value",
        ],
    },
    "general": {
        "label": "General Quality",
        "criteria": "accuracy, completeness, clarity, usefulness, and reasoning quality",
        "keywords": [],  # fallback — matches everything
    },
}


def detect_criteria(prompt: str) -> str:
    """Analyze the prompt and return the best-matching criteria preset key.

    Scores each preset by counting keyword matches, returns the highest.
    Falls back to 'general' if no strong signal.
    """
    prompt_lower = prompt.lower()
    scores: dict[str, int] = {}

    for key, preset in CRITERIA_PRESETS.items():
        if key == "general":
            continue
        score = sum(1 for kw in preset["keywords"] if kw in prompt_lower)
        if score > 0:
            scores[key] = score

    if not scores:
        return "general"

    return max(scores, key=scores.get)


def get_judge_system_prompt(criteria_key: str = "general") -> str:
    """Build the judge system prompt using the selected criteria preset."""
    preset = CRITERIA_PRESETS.get(criteria_key, CRITERIA_PRESETS["general"])
    criteria = preset["criteria"]

    return (
        f"You are an impartial AI response evaluator. Evaluate responses based on: "
        f"{criteria}. "
        f"Be fair and objective. Do not favor any particular AI model. "
        f"Respond ONLY with the requested JSON format."
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

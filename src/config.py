"""Loads environment variables and defines model configurations."""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")

# Configurable constants
TIMEOUT = 120
TEMPERATURE = 0.7
JUDGE_TEMPERATURE = 0.3
MAX_TOKENS = 4096


@dataclass
class ModelConfig:
    name: str
    model_string: str
    api_key_env_var: str
    base_url: str | None = None
    api_key: str | None = field(default=None, repr=False)

    @property
    def available(self) -> bool:
        return self.api_key is not None and len(self.api_key) > 0


def _load_models() -> dict[str, ModelConfig]:
    configs = {
        "Claude": ModelConfig(
            name="Claude",
            model_string="claude-opus-4-6",
            api_key_env_var="ANTHROPIC_API_KEY",
        ),
        "GPT-5.2": ModelConfig(
            name="GPT-5.2",
            model_string="gpt-5.2",
            api_key_env_var="OPENAI_API_KEY",
        ),
        "Gemini": ModelConfig(
            name="Gemini",
            model_string="gemini-2.5-flash",
            api_key_env_var="GOOGLE_API_KEY",
        ),
        "Grok": ModelConfig(
            name="Grok",
            model_string="grok-4-1-fast-non-reasoning",
            api_key_env_var="XAI_API_KEY",
            base_url="https://api.x.ai/v1",
        ),
    }

    logger = logging.getLogger(__name__)

    for cfg in configs.values():
        key = os.environ.get(cfg.api_key_env_var, "").strip()
        if key:
            cfg.api_key = key
        else:
            logger.warning(
                "API key %s not set — %s will be skipped.",
                cfg.api_key_env_var,
                cfg.name,
            )

    return configs


MODELS: dict[str, ModelConfig] = _load_models()


def get_available_models(subset: list[str] | None = None) -> dict[str, ModelConfig]:
    """Return models that have valid API keys, optionally filtered to a subset."""
    available = {k: v for k, v in MODELS.items() if v.available}
    if subset:
        name_map = {n.lower().replace("-", "").replace("_", ""): n for n in available}
        filtered = {}
        for s in subset:
            key = s.lower().replace("-", "").replace("_", "")
            if key in name_map:
                real = name_map[key]
                filtered[real] = available[real]
        return filtered
    return available

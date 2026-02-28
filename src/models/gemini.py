"""Google Gemini API caller."""

import asyncio

from google import genai
from google.genai.types import GenerateContentConfig

from ..config import MODELS, MAX_TOKENS

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        cfg = MODELS["Gemini"]
        _client = genai.Client(api_key=cfg.api_key)
    return _client


async def call_gemini(prompt: str, system: str = "", temperature: float = 0.7) -> str:
    client = _get_client()
    cfg = MODELS["Gemini"]

    config = GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=MAX_TOKENS,
    )
    if system:
        config.system_instruction = system

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=cfg.model_string,
        contents=prompt,
        config=config,
    )
    return response.text

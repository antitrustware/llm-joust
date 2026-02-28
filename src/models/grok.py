"""xAI Grok API caller (OpenAI-compatible)."""

from openai import AsyncOpenAI

from ..config import MODELS, MAX_TOKENS

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        cfg = MODELS["Grok"]
        _client = AsyncOpenAI(
            api_key=cfg.api_key,
            base_url=cfg.base_url,
        )
    return _client


async def call_grok(prompt: str, system: str = "", temperature: float = 0.7) -> str:
    client = _get_client()
    cfg = MODELS["Grok"]

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = await client.chat.completions.create(
        model=cfg.model_string,
        max_completion_tokens=MAX_TOKENS,
        temperature=temperature,
        messages=messages,
    )
    return response.choices[0].message.content

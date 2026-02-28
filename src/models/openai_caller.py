"""OpenAI GPT-5.2 API caller."""

from openai import AsyncOpenAI

from ..config import MODELS, MAX_TOKENS

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        cfg = MODELS["GPT-5.2"]
        _client = AsyncOpenAI(api_key=cfg.api_key)
    return _client


async def call_gpt4o(prompt: str, system: str = "", temperature: float = 0.7) -> str:
    client = _get_client()
    cfg = MODELS["GPT-5.2"]

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

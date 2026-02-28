"""Anthropic Claude Opus 4.6 API caller with extended thinking."""

from anthropic import AsyncAnthropic

from ..config import MODELS, MAX_TOKENS

_client: AsyncAnthropic | None = None

# Budget for extended thinking (tokens spent "thinking" before answering)
THINKING_BUDGET = 10000


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        cfg = MODELS["Claude"]
        _client = AsyncAnthropic(api_key=cfg.api_key)
    return _client


async def call_claude(prompt: str, system: str = "", temperature: float = 0.7) -> str:
    client = _get_client()
    cfg = MODELS["Claude"]

    # Adaptive thinking: model decides when/how much to think
    # temperature must be 1 when thinking is enabled
    kwargs: dict = dict(
        model=cfg.model_string,
        max_tokens=MAX_TOKENS + THINKING_BUDGET,
        temperature=1,
        thinking={
            "type": "adaptive",
        },
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        kwargs["system"] = system

    response = await client.messages.create(**kwargs)

    # Response contains thinking blocks + text blocks; extract the text
    for block in response.content:
        if block.type == "text":
            return block.text

    # Fallback if no text block found
    return response.content[-1].text

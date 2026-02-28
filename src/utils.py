"""Shared helpers: retry logic, timeout, logging setup."""

import asyncio
import logging
import random
from pathlib import Path
from typing import Callable, Awaitable

from .config import TIMEOUT


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "multi_llm.log"),
        ],
    )


async def with_timeout(coro: Awaitable, timeout: float = TIMEOUT):
    """Wrap an awaitable with a timeout."""
    return await asyncio.wait_for(coro, timeout=timeout)


async def retry_with_backoff(
    fn: Callable[..., Awaitable],
    *args,
    retries: int = 3,
    base_delay: float = 1.0,
    **kwargs,
):
    """Call an async function with exponential backoff on failure."""
    last_exc = None
    for attempt in range(retries):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if attempt < retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                logging.getLogger(__name__).warning(
                    "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                    attempt + 1,
                    retries,
                    fn.__name__,
                    e,
                    delay,
                )
                await asyncio.sleep(delay)
    raise last_exc

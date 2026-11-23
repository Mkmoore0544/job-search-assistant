from abc import ABC, abstractmethod
import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from app.schemas import JobCreate


class JobProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, keywords: list[str], locations: list[str]) -> list[JobCreate]:
        """Retrieve authorized public listings."""


T = TypeVar("T")


async def with_retries(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    initial_delay: float = 0.5,
) -> T:
    for attempt in range(attempts):
        try:
            return await operation()
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(initial_delay * (2 ** attempt))
    raise RuntimeError("Retry operation did not complete")

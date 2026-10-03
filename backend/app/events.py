from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: str, payload: dict[str, Any]) -> None:
        message = json.dumps({"event": event, "payload": payload})
        dead: list[asyncio.Queue[str]] = []
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead.append(queue)
        for queue in dead:
            self.unsubscribe(queue)

    async def stream(self, queue: asyncio.Queue[str]) -> AsyncIterator[str]:
        try:
            while True:
                message = await queue.get()
                yield f"data: {message}\n\n"
        finally:
            self.unsubscribe(queue)


bus = EventBus()

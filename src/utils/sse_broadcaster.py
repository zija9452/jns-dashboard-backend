"""
Minimal in-process Server-Sent Events broadcaster.

Used to push instant "something changed, go refetch" pings to connected
browsers (e.g. the shop order notification badges) without polling Neon on
every tick. Single-process only - if the backend ever runs multiple worker
processes, subscribers in one process won't hear publishes from another.
"""
import asyncio


class SSEBroadcaster:
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def publish(self, event: str = "update") -> None:
        for queue in list(self._subscribers):
            await queue.put(event)

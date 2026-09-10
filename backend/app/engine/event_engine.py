from dataclasses import dataclass
from typing import Any


@dataclass
class Event:
    type: str
    data: Any


class EventEngine:
    def __init__(self):
        self.queue = []

    async def put(self, event: Event):
        self.queue.append(event)

    async def get_all(self):
        events = list(self.queue)
        self.queue.clear()
        return events

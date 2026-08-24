import asyncio
from typing import Set

class EventBus:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance.waiters = set()
        return cls._instance

    def publish_new_job(self):
        for event in self.waiters:
            event.set()
            
    async def wait_for_job(self, timeout: float = 5.0):
        event = asyncio.Event()
        self.waiters.add(event)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        finally:
            self.waiters.discard(event)

event_bus = EventBus()
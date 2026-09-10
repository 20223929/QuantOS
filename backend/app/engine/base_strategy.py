from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    name = "base"

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass

    def on_bar(self, bar):
        return None

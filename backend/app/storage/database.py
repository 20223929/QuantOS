from pathlib import Path


DEFAULT_DB_PATH = Path("data/quntos.db")


class Database:
    def __init__(self, url: str | None = None):
        self.url = url or f"sqlite:///{DEFAULT_DB_PATH}"

    def connect(self):
        return self.url

from typing import Generic, TypeVar

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, session):
        self.session = session

    def save(self, record: T) -> T:
        self.session.add(record)
        self.session.commit()
        return record

    def all(self):
        return self.session.query(self.model).all()

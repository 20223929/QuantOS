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

    def get(self, record_id):
        return self.session.get(self.model, record_id)

    def delete(self, record):
        self.session.delete(record)
        self.session.commit()

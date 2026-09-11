"""Persistence abstraction foundation."""


class Repository:
    def __init__(self):
        self.items = []

    def save(self, item):
        self.items.append(item)
        return item

    def all(self):
        return list(self.items)

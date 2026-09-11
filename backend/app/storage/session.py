class Session:
    def __init__(self, database):
        self.database = database

    def begin(self):
        return self.database.connect()

    def close(self):
        return None

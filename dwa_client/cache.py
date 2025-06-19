import sqlite3, json, time
from typing import Any, Optional


class Cache:
    def get(self, key: str) -> Optional[Any]: ...
    def put(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    def invalidate(self, key: str) -> None: ...


class SQLiteCache(Cache):
    def __init__(self, db_path: str = ":memory:") -> None:
        self._con = sqlite3.connect(db_path, check_same_thread=False)
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS resources "
            "(url TEXT PRIMARY KEY, body TEXT, expiry REAL)"
        )

    def get(self, key: str):
        row = self._con.execute(
            "SELECT body, expiry FROM resources WHERE url = ?", (key,)
        ).fetchone()
        if not row:
            return None
        body, expiry = row
        if expiry and expiry < time.time():
            self.invalidate(key)
            return None
        return body

    def put(self, key: str, value: Any, ttl: int | None = 3600):
        expiry = (time.time() + ttl) if ttl else None
        self._con.execute(
            "REPLACE INTO resources(url, body, expiry) VALUES (?,?,?)",
            (key, value, expiry),
        )
        self._con.commit()

    def invalidate(self, key: str):
        self._con.execute("DELETE FROM resources WHERE url=?", (key,))
        self._con.commit()


class NullCache(Cache):
    def get(self, key):
        return None

    def put(self, key, value, ttl=None):
        pass

    def invalidate(self, key):
        pass

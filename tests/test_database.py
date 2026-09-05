import sqlite3
import tempfile
import unittest
from pathlib import Path

from dinnercue.db import init_db


class DatabaseTests(unittest.TestCase):
    def test_social_schema_is_created(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dinnercue.db"
            init_db(path)
            connection = sqlite3.connect(path)
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
            finally:
                connection.close()

        self.assertTrue({
            "users",
            "friendships",
            "reviews",
            "subscriptions",
            "recommendations",
        }.issubset(tables))


if __name__ == "__main__":
    unittest.main()

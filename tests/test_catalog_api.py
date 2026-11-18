import tempfile
import unittest
from pathlib import Path

from flask import Flask

from dinnercue.api import register_api


class CatalogApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_directory = tempfile.TemporaryDirectory()
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret",
            DINNERCUE_DATABASE_PATH=Path(cls.temp_directory.name) / "test.db",
            TMDB_API_KEY="",
            OMDB_API_KEY="",
        )
        register_api(cls.app)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.temp_directory.cleanup()

    def test_fresh_install_has_starter_recommendations(self):
        response = self.client.get("/api/catalog/tmdb/discover/movie")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-DinnerCue-Catalog"], "starter")
        self.assertGreaterEqual(len(response.json["results"]), 10)

    def test_starter_catalog_supports_search_and_related_titles(self):
        search = self.client.get("/api/catalog/tmdb/search/multi?query=dune")
        self.assertEqual(search.json["results"][0]["title"], "Dune")
        related = self.client.get("/api/catalog/tmdb/movie/438631/recommendations")
        self.assertNotIn(438631, [item["id"] for item in related.json["results"]])
        self.assertGreater(len(related.json["results"]), 5)

    def test_status_explains_starter_mode(self):
        response = self.client.get("/api/catalog/status")
        self.assertEqual(response.json, {
            "mode": "starter",
            "tmdb_configured": False,
            "omdb_configured": False,
        })

    def test_proxy_rejects_unknown_resources(self):
        self.assertEqual(self.client.get("/api/catalog/tmdb/configuration").status_code, 404)


if __name__ == "__main__":
    unittest.main()

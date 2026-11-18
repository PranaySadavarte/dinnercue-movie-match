import unittest
from unittest.mock import Mock, patch

import requests
from flask import Flask

from dinnercue.catalog import clear_catalog_cache, fetch_tmdb


class CatalogResilienceTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TMDB_API_KEY"] = "test-key"
        clear_catalog_cache()

    @staticmethod
    def response(payload, status=200, headers=None):
        response = Mock()
        response.status_code = status
        response.headers = headers or {}
        response.json.return_value = payload
        if status >= 400:
            response.raise_for_status.side_effect = requests.HTTPError(response=response)
        return response

    def test_repeated_catalog_request_uses_cache(self):
        response = self.response({"results": [{"id": 1}]})
        with self.app.app_context(), patch("dinnercue.catalog.requests.get", return_value=response) as get:
            first, first_source = fetch_tmdb("discover/movie", {"page": "1"})
            second, second_source = fetch_tmdb("discover/movie", {"page": "1"})

        self.assertEqual(first, second)
        self.assertEqual(first_source, "tmdb")
        self.assertEqual(second_source, "cache")
        self.assertEqual(get.call_count, 1)

    def test_retryable_failure_is_retried(self):
        busy = self.response({}, status=503)
        ready = self.response({"results": [{"id": 2}]})
        with self.app.app_context(), patch(
            "dinnercue.catalog.requests.get", side_effect=[busy, ready]
        ) as get, patch("dinnercue.catalog.time.sleep"):
            data, source = fetch_tmdb("discover/movie", {})

        self.assertEqual(data["results"][0]["id"], 2)
        self.assertEqual(source, "tmdb")
        self.assertEqual(get.call_count, 2)

    def test_client_error_is_not_retried(self):
        bad_request = self.response({}, status=400)
        with self.app.app_context(), patch(
            "dinnercue.catalog.requests.get", return_value=bad_request
        ) as get, self.assertRaises(requests.HTTPError):
            fetch_tmdb("discover/movie", {})
        self.assertEqual(get.call_count, 1)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from flask import Flask

from dinnercue.api import register_api


class SocialApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_directory = tempfile.TemporaryDirectory()
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret",
            DINNERCUE_DATABASE_PATH=Path(cls.temp_directory.name) / "test.db",
        )
        register_api(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.temp_directory.cleanup()

    def setUp(self):
        from dinnercue.db import connect

        connection = connect(self.app.config["DINNERCUE_DATABASE_PATH"])
        try:
            for table in ("user_feedback", "recommendations", "subscriptions", "reviews", "friendships", "user_profiles", "users"):
                connection.execute(f"DELETE FROM {table}")
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def register(client, username, display_name):
        return client.post("/api/auth/register", json={
            "username": username,
            "display_name": display_name,
            "password": "good-password",
        })

    def test_registration_login_and_current_user(self):
        client = self.app.test_client()
        response = self.register(client, "maya", "Maya")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(client.get("/api/auth/me").json["user"]["username"], "maya")

        client.post("/api/auth/logout")
        self.assertEqual(client.get("/api/auth/me").status_code, 401)
        self.assertEqual(client.post("/api/auth/login", json={
            "username": "maya", "password": "good-password"
        }).status_code, 200)

    def test_guest_mode_does_not_require_an_account(self):
        client = self.app.test_client()
        self.assertEqual(client.post("/api/auth/guest").status_code, 200)
        response = client.get("/api/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["mode"], "guest")
        self.assertIsNone(response.json["user"])

    def test_google_status_explains_when_credentials_are_missing(self):
        response = self.app.test_client().get("/api/auth/google/status")
        self.assertEqual(response.json, {"configured": False})

    def test_friend_request_trust_and_review_feed(self):
        maya = self.app.test_client()
        pranay = self.app.test_client()
        maya_id = self.register(maya, "maya", "Maya").json["user"]["id"]
        pranay_id = self.register(pranay, "pranay", "Pranay").json["user"]["id"]

        request_response = pranay.post("/api/friends/requests", json={"username": "maya"})
        self.assertEqual(request_response.status_code, 201)
        self.assertEqual(maya.post(f"/api/friends/{pranay_id}/accept").status_code, 200)
        self.assertEqual(pranay.patch(f"/api/friends/{maya_id}/trust", json={"trust_weight": 0.9}).status_code, 200)

        review_response = maya.post("/api/reviews", json={
            "tmdb_id": 329865,
            "media_type": "movie",
            "rating": 4.5,
            "review_text": "Quiet, thoughtful science fiction.",
        })
        self.assertEqual(review_response.status_code, 201)

        feed = pranay.get("/api/reviews/feed")
        self.assertEqual(feed.status_code, 200)
        self.assertEqual(feed.json["reviews"][0]["username"], "maya")
        self.assertEqual(feed.json["reviews"][0]["rating"], 4.5)

    def test_review_feed_is_private_to_user_and_friends(self):
        maya = self.app.test_client()
        stranger = self.app.test_client()
        self.register(maya, "maya", "Maya")
        self.register(stranger, "stranger", "Stranger")
        maya.post("/api/reviews", json={"tmdb_id": 1, "rating": 5})
        self.assertEqual(stranger.get("/api/reviews/feed").json["reviews"], [])

    def test_feedback_can_be_submitted_without_an_account(self):
        client = self.app.test_client()
        response = client.post("/api/feedback", json={
            "category": "confusing",
            "message": "The recommendation reason needs more detail.",
            "page_path": "/",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["status"], "received")

    def test_feedback_rejects_too_short_messages(self):
        client = self.app.test_client()
        self.assertEqual(client.post("/api/feedback", json={
            "category": "bug", "message": "broken"
        }).status_code, 400)

    def test_subscriptions_can_be_replaced_and_read(self):
        client = self.app.test_client()
        self.register(client, "maya", "Maya")
        response = client.put("/api/subscriptions", json={
            "region": "US",
            "subscriptions": [
                {"provider_id": 8, "provider_name": "Netflix"},
                {"provider_id": 350, "provider_name": "Apple TV+"},
            ],
        })
        self.assertEqual(response.status_code, 200)
        saved = client.get("/api/subscriptions").json["subscriptions"]
        self.assertEqual([item["provider_name"] for item in saved], ["Apple TV+", "Netflix"])

    def test_onboarding_profile_and_watched_titles_persist(self):
        client = self.app.test_client()
        self.register(client, "maya", "Maya")
        payload = {
            "favorite_genres": [35, 878],
            "moods": ["feel-good"],
            "content_types": ["movie", "tv"],
            "runtime_preference": "short",
            "subscriptions": [{"provider_id": 8, "provider_name": "Netflix"}],
            "watched_titles": [{
                "id": 438631, "tmdb_id": 438631, "media_type": "movie",
                "title": "Dune", "poster_path": "/poster.jpg", "year": "2021",
            }],
        }
        saved = client.put("/api/onboarding", json=payload)
        self.assertEqual(saved.status_code, 200)
        profile = client.get("/api/onboarding").json
        self.assertTrue(profile["onboarding_completed"])
        self.assertEqual(profile["favorite_genres"], ["35", "878"])
        self.assertEqual(profile["subscriptions"][0]["provider_name"], "Netflix")
        self.assertEqual(profile["watched_titles"][0]["title"], "Dune")

    def test_group_board_endpoint_ignores_absent_votes(self):
        client = self.app.test_client()
        response = client.post("/api/recommendations/group-board", json={
            "absent_friend_ids": ["lee"],
            "candidates": [
                {"tmdb_id": 1, "title": "Arrival", "votes": [{"friend_id": "lee", "weight": 4}]},
                {"tmdb_id": 2, "title": "Dune", "votes": [{"friend_id": "maya", "weight": 2}]},
            ],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["verdict"]["leader"]["title"], "Dune")


if __name__ == "__main__":
    unittest.main()

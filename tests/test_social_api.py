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
            for table in ("user_feedback", "recommendations", "subscriptions", "reviews", "friendships", "users"):
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


if __name__ == "__main__":
    unittest.main()

import unittest

from dinnercue.recommendations import friend_signal, rank_candidates


class RecommendationTests(unittest.TestCase):
    def test_trusted_similar_friend_has_more_influence(self):
        score = friend_signal([
            {"rating": 5, "trust": 1, "taste_match": 1},
            {"rating": 1, "trust": 0.1, "taste_match": 0.2},
        ])
        self.assertGreater(score, 0.9)

    def test_subscription_and_friends_can_change_the_winner(self):
        ranked = rank_candidates([
            {
                "tmdb_id": 1,
                "title": "Personal Match",
                "personal_match": 1,
                "context_match": 0.7,
                "novelty": 0.5,
                "on_subscribed_service": False,
                "friends": [],
            },
            {
                "tmdb_id": 2,
                "title": "Friends' Pick",
                "personal_match": 0.7,
                "context_match": 0.9,
                "novelty": 0.8,
                "on_subscribed_service": True,
                "friends": [{
                    "name": "Maya",
                    "rating": 5,
                    "trust": 0.9,
                    "taste_match": 0.9,
                    "recommended": True,
                }],
            },
        ])
        self.assertEqual(ranked[0].title, "Friends' Pick")
        self.assertIn("Recommended by Maya", ranked[0].reasons)
        self.assertIn("Available on one of your subscriptions", ranked[0].reasons)

    def test_scores_are_clamped(self):
        ranked = rank_candidates([{
            "tmdb_id": 3,
            "title": "Bounded",
            "personal_match": 4,
            "context_match": -2,
            "novelty": 10,
            "on_subscribed_service": True,
            "friends": [],
        }])
        self.assertLessEqual(ranked[0].score, 100)
        self.assertGreaterEqual(ranked[0].score, 0)


if __name__ == "__main__":
    unittest.main()


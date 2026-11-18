import unittest

from dinnercue.group_choice import build_night_board, night_verdict


class GroupChoiceTests(unittest.TestCase):
    def test_absent_friend_votes_do_not_decide_tonight(self):
        board = build_night_board([
            {"tmdb_id": 1, "title": "Arrival", "votes": [
                {"friend_id": "maya", "weight": 1},
                {"friend_id": "lee", "weight": 3},
            ]},
            {"tmdb_id": 2, "title": "Dune", "votes": [
                {"friend_id": "maya", "weight": 2},
            ]},
        ], absent_friend_ids=["lee"])

        self.assertEqual(board[0]["title"], "Dune")
        arrival = next(row for row in board if row["title"] == "Arrival")
        self.assertEqual(arrival["votes"], 1)
        self.assertEqual(arrival["waiting_for"], ["lee"])
        self.assertEqual(night_verdict(board)["leader"]["title"], "Dune")

    def test_ties_are_explicit_and_deterministic(self):
        board = build_night_board([
            {"tmdb_id": 2, "title": "Dune", "votes": [{"friend_id": "a", "weight": 1}]},
            {"tmdb_id": 1, "title": "Arrival", "votes": [{"friend_id": "b", "weight": 1}]},
        ])
        verdict = night_verdict(board)
        self.assertTrue(verdict["tied"])
        self.assertEqual([row["title"] for row in verdict["finalists"]], ["Arrival", "Dune"])

    def test_no_votes_has_clear_state(self):
        board = build_night_board([{"tmdb_id": 1, "title": "Arrival", "votes": []}])
        self.assertEqual(night_verdict(board), {"state": "no-votes"})


if __name__ == "__main__":
    unittest.main()

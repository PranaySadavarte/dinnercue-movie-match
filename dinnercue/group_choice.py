"""Presence-aware standings for deciding what a group watches tonight.

The arithmetic and state model are adapted from Popcorn Vote's MIT-licensed
standings module. DinnerCue keeps the implementation server-side and uses
friend IDs plus weighted votes instead of device tokens.
"""

import math


def build_night_board(candidates, absent_friend_ids=None):
    absent_order = [str(friend_id) for friend_id in (absent_friend_ids or [])]
    absent = set(absent_order)
    board = []

    for candidate in candidates:
        present_votes = 0.0
        all_votes = 0.0
        blocked = set()
        votes = candidate.get("votes", [])
        if not isinstance(votes, list) or len(votes) > 100:
            raise ValueError("votes must be a list with no more than 100 entries")
        for vote in votes:
            friend_id = str(vote["friend_id"])
            weight = float(vote.get("weight", 1))
            if not math.isfinite(weight) or not 0 <= weight <= 5:
                raise ValueError("vote weight must be between 0 and 5")
            all_votes += weight
            if friend_id in absent:
                if weight:
                    blocked.add(friend_id)
            else:
                present_votes += weight

        board.append({
            "tmdb_id": int(candidate["tmdb_id"]),
            "title": str(candidate["title"]),
            "votes": round(present_votes, 2),
            "all_votes": round(all_votes, 2),
            "waiting_for": [friend_id for friend_id in absent_order if friend_id in blocked],
        })

    return sorted(board, key=lambda row: (-row["votes"], row["title"].casefold()))


def night_verdict(board):
    if not any(row["all_votes"] > 0 for row in board):
        return {"state": "no-votes"}
    eligible = [row for row in board if not row["waiting_for"] and row["votes"] > 0]
    if not eligible:
        blockers = []
        for row in board:
            for friend_id in row["waiting_for"]:
                if friend_id not in blockers:
                    blockers.append(friend_id)
        return {"state": "all-waiting", "friend_ids": blockers}
    high_score = max(row["votes"] for row in eligible)
    finalists = [row for row in eligible if row["votes"] == high_score]
    return {
        "state": "ready",
        "leader": finalists[0],
        "tied": len(finalists) > 1,
        "finalists": finalists,
    }

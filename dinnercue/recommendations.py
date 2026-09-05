from dataclasses import dataclass


WEIGHTS = {
    "personal": 0.35,
    "friends": 0.25,
    "availability": 0.20,
    "context": 0.10,
    "novelty": 0.10,
}


def _unit(value):
    return max(0.0, min(1.0, float(value or 0)))


@dataclass(frozen=True)
class RankedTitle:
    tmdb_id: int
    title: str
    score: float
    reasons: tuple[str, ...]
    breakdown: dict[str, float]

    def as_dict(self):
        return {
            "tmdb_id": self.tmdb_id,
            "title": self.title,
            "score": self.score,
            "reasons": list(self.reasons),
            "breakdown": self.breakdown,
        }


def friend_signal(friends):
    """Return a trust- and taste-weighted friend score in the 0..1 range."""
    total_weight = 0.0
    weighted_ratings = 0.0
    for friend in friends or []:
        influence = _unit(friend.get("trust", 0.5)) * _unit(friend.get("taste_match", 0.5))
        if friend.get("recommended"):
            influence *= 1.15
        total_weight += influence
        weighted_ratings += _unit(float(friend.get("rating", 0)) / 5) * influence
    return _unit(weighted_ratings / total_weight) if total_weight else 0.0


def rank_candidate(candidate):
    personal = _unit(candidate.get("personal_match"))
    friends = friend_signal(candidate.get("friends"))
    availability = 1.0 if candidate.get("on_subscribed_service") else 0.0
    context = _unit(candidate.get("context_match"))
    novelty = _unit(candidate.get("novelty"))

    raw = {
        "personal": personal,
        "friends": friends,
        "availability": availability,
        "context": context,
        "novelty": novelty,
    }
    breakdown = {name: round(value * WEIGHTS[name] * 100, 1) for name, value in raw.items()}
    score = round(sum(breakdown.values()), 1)

    reasons = []
    friend_names = [friend.get("name") for friend in candidate.get("friends", []) if friend.get("name")]
    if friends >= 0.7 and friend_names:
        reasons.append(f"Recommended by {', '.join(friend_names[:2])}")
    if personal >= 0.7:
        reasons.append("Strong match for your viewing history")
    if availability:
        reasons.append("Available on one of your subscriptions")
    if context >= 0.8:
        reasons.append("Fits tonight's preferences")
    if novelty >= 0.8:
        reasons.append("Adds something fresh to your recent viewing")

    return RankedTitle(
        tmdb_id=int(candidate["tmdb_id"]),
        title=str(candidate["title"]),
        score=score,
        reasons=tuple(reasons[:3]),
        breakdown=breakdown,
    )


def rank_candidates(candidates):
    ranked = [rank_candidate(candidate) for candidate in candidates]
    return sorted(ranked, key=lambda item: (-item.score, item.title.lower()))


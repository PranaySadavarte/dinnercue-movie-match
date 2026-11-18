# Public repository research and product ideas

Research date: November 18, 2026

## What informed this milestone

- [Streamline](https://github.com/abhichandra21/streamline) (MIT): its short “Mood Match” flow supports asking about tonight separately from long-term taste. DinnerCue now captures a lightweight mood and dinner-length context during onboarding.
- [Watchly](https://github.com/TimilsinaBimal/Watchly) (license not verified): its taste-profile approach combines genres with watched history and explains rows with “Because you watched…”. Used as product inspiration only.
- [PlexSuggest](https://github.com/aritchie/plexsuggest) (license not verified): its recency-weighted watch-history profile suggests that recent watches should matter more than very old history. Used as product inspiration only.
- [Popcorn Vote](https://github.com/Stadicus/popcorn-vote) (MIT): fair group voting, present-member handling, a tie breaker, shared diary, and PWA/mobile-first design remain strong references for the friends stage.
- [MovieNight](https://github.com/sekmo/movienight) (MIT): intersecting two friends’ watchlists is a simple, high-value social recommendation pattern.
- [Movary](https://github.com/leepeuker/movary) and [ScreenJournal](https://github.com/mtlynch/screenjournal): imports, private viewing history, statistics, and community review digests are useful longer-term ideas. No code was copied.

## Recommended roadmap

### Next

1. Add a small “Why this pick?” panel showing subscription, genre, watched-title seed, runtime, and mood contributions.
2. Let signed-in users edit their services and taste profile without repeating onboarding.
3. Add a “Not tonight” action so dismissed titles are suppressed for a few weeks.
4. Add a dinner-mode constraint for episode length, family-safe content, language, and number of people watching.

### Friends stage

1. Each user publishes 5–10 evergreen favorites and optionally a short note for each.
2. Show an overlap shelf: “You and Maya both want to watch these.”
3. Add trust by category rather than one global score—for example, trust one friend for horror and another for documentaries.
4. Create a private dinner room where present friends combine subscriptions and vote on a five-title shortlist.
5. Preserve recommendation provenance: who suggested it, when, and whether the recipient watched and liked it.

### Later

1. Import Letterboxd CSV, Netflix viewing activity, Trakt, Plex, or Jellyfin history.
2. Add recency decay so the profile adapts as taste changes.
3. Add diversity controls to prevent twelve nearly identical recommendations.
4. Offer PWA installation and an offline cached shortlist for the dining table.
5. Add a private weekly digest of highly rated friend reviews.

## Licensing rule

Only clearly permissive source may be adapted. Repositories with missing, unclear,
or copyleft licenses are references for product behavior only. Any future adapted
implementation must be recorded in `THIRD_PARTY_NOTICES.md`.

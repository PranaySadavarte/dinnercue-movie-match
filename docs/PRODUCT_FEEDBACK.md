# DinnerCue product feedback

## Current assessment

DinnerCue has a distinctive premise and a solid cinematic visual direction. Its strongest value is not catalog browsing; it is reducing the time and disagreement involved in choosing something to watch. Product decisions should therefore optimize for fast, explainable choices.

## Improvements completed

- Reduced the oversized homepage introduction so useful content appears sooner.
- Moved recommendations ahead of trailer browsing.
- Changed long recommendation grids into compact horizontal poster rails.
- Added a private in-app feedback form with validation and database storage.
- Preserved a usable starter catalog when live movie data is unavailable.

## Highest-priority next improvements

1. Add visible account, profile, and friend activity screens backed by the existing social API.
2. Incorporate streaming subscriptions into the actual ranking query.
3. Show trusted-friend recommendations and explanations directly on title cards.
4. Replace browser-only watched and watchlist data with account-backed persistence.
5. Add empty, loading, offline, and movie-provider states to browser-level tests.

## Quality checklist

- A fresh user sees recommendations without setup.
- Search, filters, Surprise Me, watched, and watchlist actions remain usable.
- Recommendation rails do not create page-level horizontal overflow.
- Keyboard focus and status messages are available to assistive technology.
- API keys never appear in page source, browser storage, logs, or Git.
- Feedback works with or without an account and rejects invalid submissions.

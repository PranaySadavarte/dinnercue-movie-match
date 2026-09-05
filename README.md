# DinnerCue Movie Match

DinnerCue Movie Match is a lightweight movie and TV discovery app. It helps users search for a title, find recommendations, save a watchlist, mark watched titles, and browse trailer links in a swipeable reel-style section.

## Features

- Movie and TV search with autocomplete suggestions
- Personalized recommendations from locally saved watched history
- Taste quiz seeded from highly rated and heavily watched titles
- Genre, runtime, and content type filters
- Watchlist and watched-history panels stored in the browser
- Surprise Me action for quick pick selection
- Swipeable trailer cards that open directly on YouTube
- JustWatch links for finding where a title is available
- Server-side foundation for users, friendships, trusted recommenders, reviews, subscriptions, and direct recommendations
- Explainable recommendation ranking that combines personal taste, trusted friends, availability, tonight's context, and novelty

## Run Locally

Run the Flask app and open `http://127.0.0.1:5000`. DinnerCue includes a small starter catalog, so recommendations and search work immediately on a fresh checkout.

For live catalog data, set your TMDb key and optional OMDb key in `.env`. Keys remain on the server and are never sent to the browser.

The optional Flask helper can serve the same page if Python dependencies are installed:

```powershell
python -m pip install -r requirements.txt
python fetchmov.py
```

The backend initializes its SQLite database in `instance/dinnercue.db`. Check it at
`http://localhost:5000/api/health`.

Run the recommendation tests with:

```powershell
python -m unittest discover -s tests -v
```

## Recommendation API

Send candidate titles to `POST /api/recommendations/rank`. Each candidate can include
`personal_match`, `friends`, `on_subscribed_service`, `context_match`, and `novelty`.
The response includes a score breakdown and short reasons suitable for showing in the UI.

## Social API

The first authenticated social flow is available under `/api`:

- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, and `GET /auth/me`
- `POST /friends/requests`, `POST /friends/<id>/accept`, `GET /friends`, and `PATCH /friends/<id>/trust`
- `POST /reviews` and `GET /reviews/feed`

Passwords are stored as secure hashes and login state uses an HTTP-only session cookie.
Set a strong `DINNERCUE_SECRET_KEY` outside development.

For the Flask helper, set environment variables before starting the server:

```powershell
$env:TMDB_API_KEY="your_tmdb_key"
$env:OMDB_API_KEY="your_omdb_key"
python fetchmov.py
```

## Notes

This version stores watched history and watchlist data in browser local storage. API keys are read by Flask and movie-service requests are proxied through allowlisted server endpoints.

import re
import threading
import time

import requests
from flask import current_app


REQUEST_TIMEOUT = 8
CATALOG_CACHE_TTL = 300
CATALOG_STALE_TTL = 3600
MAX_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
ALLOWED_RESOURCES = re.compile(
    r"^(search/(movie|multi)|discover/(movie|tv)|(movie|tv)/\d+/(recommendations|videos))$"
)

_cache = {}
_cache_lock = threading.Lock()


def _cache_key(resource, params):
    return resource, tuple(sorted((str(key), str(value)) for key, value in params.items()))


def _cached(resource, params, *, allow_stale=False):
    entry = _cache.get(_cache_key(resource, params))
    if not entry:
        return None
    age = time.monotonic() - entry[0]
    limit = CATALOG_STALE_TTL if allow_stale else CATALOG_CACHE_TTL
    return entry[1] if age <= limit else None


def clear_catalog_cache():
    """Clear process-local catalog data. Primarily useful for tests and admin tasks."""
    with _cache_lock:
        _cache.clear()

STARTER_TITLES = [
    {"id": 438631, "media_type": "movie", "title": "Dune", "release_date": "2021-10-22", "vote_average": 7.8, "vote_count": 14000, "genre_ids": [12, 18, 878], "overview": "A gifted young man must travel to the universe's most dangerous planet to secure his family's future."},
    {"id": 329865, "media_type": "movie", "title": "Arrival", "release_date": "2016-11-11", "vote_average": 7.6, "vote_count": 18000, "genre_ids": [18, 9648, 878], "overview": "A linguist works with the military to communicate with mysterious visitors."},
    {"id": 496243, "media_type": "movie", "title": "Parasite", "release_date": "2019-05-30", "vote_average": 8.5, "vote_count": 19000, "genre_ids": [35, 18, 53], "overview": "A struggling family slowly works its way into the home of a wealthy household."},
    {"id": 545611, "media_type": "movie", "title": "Everything Everywhere All at Once", "release_date": "2022-03-25", "vote_average": 7.8, "vote_count": 7000, "genre_ids": [28, 12, 35, 878], "overview": "An overwhelmed laundromat owner is swept into a strange adventure across many possible lives."},
    {"id": 546554, "media_type": "movie", "title": "Knives Out", "release_date": "2019-11-27", "vote_average": 7.8, "vote_count": 13000, "genre_ids": [35, 80, 9648], "overview": "A detective investigates the death of the patriarch of an eccentric family."},
    {"id": 569094, "media_type": "movie", "title": "Spider-Man: Across the Spider-Verse", "release_date": "2023-06-02", "vote_average": 8.3, "vote_count": 8000, "genre_ids": [16, 28, 12], "overview": "Miles Morales encounters a team of Spider-People charged with protecting the multiverse."},
    {"id": 666277, "media_type": "movie", "title": "Past Lives", "release_date": "2023-06-02", "vote_average": 7.7, "vote_count": 2000, "genre_ids": [18, 10749], "overview": "Two childhood friends reunite in New York decades after being separated."},
    {"id": 840430, "media_type": "movie", "title": "The Holdovers", "release_date": "2023-10-27", "vote_average": 7.7, "vote_count": 2000, "genre_ids": [35, 18], "overview": "A curmudgeonly teacher remains at school during the holidays with students who have nowhere to go."},
    {"id": 872585, "media_type": "movie", "title": "Oppenheimer", "release_date": "2023-07-21", "vote_average": 8.1, "vote_count": 10000, "genre_ids": [18, 36], "overview": "The story of the scientist who helped develop the atomic bomb and faced its consequences."},
    {"id": 587792, "media_type": "movie", "title": "Palm Springs", "release_date": "2020-07-10", "vote_average": 7.3, "vote_count": 3200, "genre_ids": [35, 10749, 878], "overview": "Two wedding guests become trapped together in a time loop."},
    {"id": 414906, "media_type": "movie", "title": "The Batman", "release_date": "2022-03-04", "vote_average": 7.7, "vote_count": 10000, "genre_ids": [80, 9648, 53], "overview": "Batman follows a trail of cryptic clues into Gotham's criminal underworld."},
    {"id": 593643, "media_type": "movie", "title": "The Menu", "release_date": "2022-11-18", "vote_average": 7.2, "vote_count": 5000, "genre_ids": [35, 27, 53], "overview": "A couple visits an exclusive restaurant where the chef has prepared unexpected surprises."},
    {"id": 76331, "media_type": "tv", "name": "Succession", "first_air_date": "2018-06-03", "vote_average": 8.3, "vote_count": 1200, "genre_ids": [18], "overview": "A media dynasty fights over control as its patriarch's health becomes uncertain."},
    {"id": 136315, "media_type": "tv", "name": "The Bear", "first_air_date": "2022-06-23", "vote_average": 8.2, "vote_count": 1300, "genre_ids": [18, 35], "overview": "A young chef returns home to run his family's sandwich shop."},
]


def _starter_for(resource, params):
    if resource.startswith("search/"):
        query = params.get("query", "").casefold()
        results = [item for item in STARTER_TITLES if query in (item.get("title") or item.get("name", "")).casefold()]
        if resource == "search/movie":
            results = [item for item in results if item["media_type"] == "movie"]
        return {"page": 1, "results": results}

    if resource.startswith("discover/"):
        media_type = resource.rsplit("/", 1)[1]
        genre = params.get("with_genres")
        results = [item for item in STARTER_TITLES if item["media_type"] == media_type]
        if genre:
            results = [item for item in results if int(genre) in item.get("genre_ids", [])]
        return {"page": 1, "results": results}

    match = re.match(r"^(movie|tv)/(\d+)/recommendations$", resource)
    if match:
        media_type, title_id = match.groups()
        return {"page": 1, "results": [item for item in STARTER_TITLES if item["media_type"] == media_type and item["id"] != int(title_id)]}

    return {"results": []}


def fetch_tmdb(resource, params):
    if not ALLOWED_RESOURCES.fullmatch(resource):
        raise ValueError("unsupported catalog resource")
    api_key = current_app.config.get("TMDB_API_KEY", "")
    if not api_key:
        return _starter_for(resource, params), "starter"

    with _cache_lock:
        cached = _cached(resource, params)
    if cached is not None:
        return cached, "cache"

    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(
                f"https://api.themoviedb.org/3/{resource}",
                params={**params, "api_key": api_key},
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code in RETRYABLE_STATUS_CODES:
                response.raise_for_status()
            response.raise_for_status()
            data = response.json()
            with _cache_lock:
                _cache[_cache_key(resource, params)] = (time.monotonic(), data)
            return data, "tmdb"
        except requests.RequestException as error:
            last_error = error
            status = getattr(error.response, "status_code", None)
            if status not in RETRYABLE_STATUS_CODES or attempt == MAX_ATTEMPTS - 1:
                break
            retry_after = getattr(error.response, "headers", {}).get("Retry-After")
            try:
                delay = min(float(retry_after), 5.0) if retry_after else 0.25 * (2 ** attempt)
            except (TypeError, ValueError):
                delay = 0.25 * (2 ** attempt)
            time.sleep(delay)

    with _cache_lock:
        stale = _cached(resource, params, allow_stale=True)
    if stale is not None:
        return stale, "stale-cache"
    raise last_error


def fetch_omdb(title):
    api_key = current_app.config.get("OMDB_API_KEY", "")
    if not api_key:
        return {"Response": "False", "Error": "OMDb is not configured."}
    response = requests.get(
        "https://www.omdbapi.com/",
        params={"apikey": api_key, "t": title},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


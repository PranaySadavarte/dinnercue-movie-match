import os

from flask import Flask, request, render_template
import requests

from dinnercue.api import register_api

app = Flask(__name__, template_folder=".")
register_api(app)

OMDB_API_KEY = os.getenv("OMDB_API_KEY", "")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
REQUEST_TIMEOUT = 8


def get_movie_details(movie_title):
    """Fetch movie details from OMDb."""
    if not OMDB_API_KEY:
        return {"Response": "False", "Error": "OMDB_API_KEY is not configured."}

    omdb_url = "https://www.omdbapi.com/"
    response = requests.get(
        omdb_url,
        params={"apikey": OMDB_API_KEY, "t": movie_title},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_related_movies(movie_title):
    """Fetch related movies from TMDb."""
    if not TMDB_API_KEY:
        return []

    tmdb_search_url = "https://api.themoviedb.org/3/search/movie"
    response = requests.get(
        tmdb_search_url,
        params={"api_key": TMDB_API_KEY, "query": movie_title},
        timeout=REQUEST_TIMEOUT,
    ).json()

    if not response.get("results"):
        return []

    movie_id = response["results"][0]["id"]

    tmdb_related_url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations"
    related_movies = requests.get(
        tmdb_related_url,
        params={"api_key": TMDB_API_KEY},
        timeout=REQUEST_TIMEOUT,
    ).json().get("results", [])

    return related_movies[:6]  # Get top 6 related movies


def get_streaming_links(movie_id):
    """Fetch streaming platform links from TMDb (JustWatch API)."""
    if not TMDB_API_KEY:
        return ["No streaming info available"]

    watch_url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers"
    response = requests.get(
        watch_url,
        params={"api_key": TMDB_API_KEY},
        timeout=REQUEST_TIMEOUT,
    ).json()

    if response.get("results") and response["results"].get("US"):
        return [provider["provider_name"] for provider in response["results"]["US"].get("flatrate", [])]

    return ["No streaming info available"]


@app.route("/", methods=["GET", "POST"])
def index():
    movie_details = None
    related_movies = []

    if request.method == "POST":
        movie_title = request.form.get("movie", "").strip()

        if not movie_title:
            return render_template("fetchmov.html", movie_details=movie_details, related_movies=related_movies)

        try:
            movie_details = get_movie_details(movie_title)
        except requests.RequestException:
            movie_details = {"Response": "False", "Error": "Movie service is unavailable. Please try again."}

        if movie_details.get("Response") == "True":
            try:
                related_movies = get_related_movies(movie_title)

                for movie in related_movies:
                    movie["streaming_links"] = get_streaming_links(movie["id"])
            except requests.RequestException:
                related_movies = []

    return render_template("fetchmov.html", movie_details=movie_details, related_movies=related_movies)


if __name__ == "__main__":
    app.run(debug=True)

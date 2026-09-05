from functools import wraps

from flask import Blueprint, current_app, jsonify, request, session
import requests
from werkzeug.security import check_password_hash, generate_password_hash

from .db import connect, init_db
from .catalog import fetch_omdb, fetch_tmdb
from .recommendations import rank_candidates


api = Blueprint("api", __name__, url_prefix="/api")


def _connection():
    return connect(current_app.config.get("DINNERCUE_DATABASE_PATH"))


def _user_dict(row):
    return {"id": row["id"], "username": row["username"], "display_name": row["display_name"]}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "authentication required"}), 401
        return view(*args, **kwargs)

    return wrapped


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


@api.get("/catalog/status")
def catalog_status():
    return jsonify({
        "mode": "live" if current_app.config.get("TMDB_API_KEY") else "starter",
        "tmdb_configured": bool(current_app.config.get("TMDB_API_KEY")),
        "omdb_configured": bool(current_app.config.get("OMDB_API_KEY")),
    })


@api.get("/catalog/tmdb/<path:resource>")
def catalog_tmdb(resource):
    params = {key: value for key, value in request.args.items() if key != "api_key"}
    try:
        data, source = fetch_tmdb(resource, params)
    except ValueError as error:
        return jsonify({"error": str(error)}), 404
    except requests.RequestException:
        return jsonify({"error": "movie catalog is temporarily unavailable"}), 502
    response = jsonify(data)
    response.headers["X-DinnerCue-Catalog"] = source
    return response


@api.get("/catalog/omdb")
def catalog_omdb():
    title = request.args.get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    try:
        return jsonify(fetch_omdb(title))
    except requests.RequestException:
        return jsonify({"Response": "False", "Error": "Movie details are temporarily unavailable."}), 502


@api.post("/auth/register")
def register():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip().lower()
    display_name = str(payload.get("display_name", "")).strip()
    password = str(payload.get("password", ""))
    if len(username) < 3 or len(display_name) < 1 or len(password) < 8:
        return jsonify({"error": "username must be 3+ characters, display name is required, and password must be 8+ characters"}), 400
    if not username.replace("_", "").isalnum():
        return jsonify({"error": "username may contain only letters, numbers, and underscores"}), 400

    connection = _connection()
    try:
        cursor = connection.execute(
            "INSERT INTO users (username, display_name, password_hash) VALUES (?, ?, ?)",
            (username, display_name, generate_password_hash(password)),
        )
        connection.commit()
        session.clear()
        session["user_id"] = cursor.lastrowid
        row = connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    except Exception as error:
        if "UNIQUE constraint failed" in str(error):
            return jsonify({"error": "username is already taken"}), 409
        raise
    finally:
        connection.close()
    return jsonify({"user": _user_dict(row)}), 201


@api.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip().lower()
    connection = _connection()
    try:
        row = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    finally:
        connection.close()
    if not row or not row["password_hash"] or not check_password_hash(row["password_hash"], str(payload.get("password", ""))):
        return jsonify({"error": "invalid username or password"}), 401
    session.clear()
    session["user_id"] = row["id"]
    return jsonify({"user": _user_dict(row)})


@api.post("/auth/logout")
def logout():
    session.clear()
    return "", 204


@api.get("/auth/me")
@login_required
def me():
    connection = _connection()
    try:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    finally:
        connection.close()
    return jsonify({"user": _user_dict(row)})


@api.post("/friends/requests")
@login_required
def request_friend():
    username = str((request.get_json(silent=True) or {}).get("username", "")).strip().lower()
    connection = _connection()
    try:
        friend = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not friend:
            return jsonify({"error": "user not found"}), 404
        if friend["id"] == session["user_id"]:
            return jsonify({"error": "you cannot add yourself"}), 400
        existing = connection.execute(
            "SELECT status FROM friendships WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)",
            (session["user_id"], friend["id"], friend["id"], session["user_id"]),
        ).fetchone()
        if existing:
            return jsonify({"error": "friendship already exists", "status": existing["status"]}), 409
        connection.execute(
            "INSERT INTO friendships (user_id, friend_id) VALUES (?, ?)",
            (session["user_id"], friend["id"]),
        )
        connection.commit()
    finally:
        connection.close()
    return jsonify({"friend": _user_dict(friend), "status": "pending"}), 201


@api.post("/friends/<int:friend_id>/accept")
@login_required
def accept_friend(friend_id):
    connection = _connection()
    try:
        cursor = connection.execute(
            "UPDATE friendships SET status = 'accepted', updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND friend_id = ? AND status = 'pending'",
            (friend_id, session["user_id"]),
        )
        connection.commit()
    finally:
        connection.close()
    if cursor.rowcount != 1:
        return jsonify({"error": "pending friend request not found"}), 404
    return jsonify({"status": "accepted"})


@api.get("/friends")
@login_required
def friends():
    connection = _connection()
    try:
        rows = connection.execute(
            """
            SELECT u.id, u.username, u.display_name, f.status, f.trust_weight,
                   CASE WHEN f.friend_id = ? THEN 1 ELSE 0 END AS incoming
            FROM friendships f
            JOIN users u ON u.id = CASE WHEN f.user_id = ? THEN f.friend_id ELSE f.user_id END
            WHERE f.user_id = ? OR f.friend_id = ?
            ORDER BY f.status, u.display_name
            """,
            (session["user_id"], session["user_id"], session["user_id"], session["user_id"]),
        ).fetchall()
    finally:
        connection.close()
    return jsonify({"friends": [dict(row) for row in rows]})


@api.patch("/friends/<int:friend_id>/trust")
@login_required
def update_trust(friend_id):
    try:
        trust = float((request.get_json(silent=True) or {}).get("trust_weight"))
    except (TypeError, ValueError):
        return jsonify({"error": "trust_weight must be between 0 and 1"}), 400
    if not 0 <= trust <= 1:
        return jsonify({"error": "trust_weight must be between 0 and 1"}), 400
    connection = _connection()
    try:
        cursor = connection.execute(
            """UPDATE friendships SET trust_weight = ?, updated_at = CURRENT_TIMESTAMP
               WHERE status = 'accepted' AND ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))""",
            (trust, session["user_id"], friend_id, friend_id, session["user_id"]),
        )
        connection.commit()
    finally:
        connection.close()
    if cursor.rowcount != 1:
        return jsonify({"error": "accepted friendship not found"}), 404
    return jsonify({"trust_weight": trust})


@api.post("/reviews")
@login_required
def save_review():
    payload = request.get_json(silent=True) or {}
    try:
        tmdb_id = int(payload["tmdb_id"])
        rating = float(payload["rating"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "tmdb_id and rating are required"}), 400
    media_type = str(payload.get("media_type", "movie"))
    if media_type not in {"movie", "tv", "short"} or not 0.5 <= rating <= 5:
        return jsonify({"error": "invalid media_type or rating"}), 400
    connection = _connection()
    try:
        connection.execute(
            """
            INSERT INTO reviews (user_id, tmdb_id, media_type, rating, review_text, contains_spoilers, watched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, tmdb_id, media_type) DO UPDATE SET
                rating = excluded.rating, review_text = excluded.review_text,
                contains_spoilers = excluded.contains_spoilers, watched_at = excluded.watched_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (session["user_id"], tmdb_id, media_type, rating, str(payload.get("review_text", "")).strip(),
             1 if payload.get("contains_spoilers") else 0, payload.get("watched_at")),
        )
        connection.commit()
    finally:
        connection.close()
    return jsonify({"status": "saved"}), 201


@api.get("/reviews/feed")
@login_required
def review_feed():
    connection = _connection()
    try:
        rows = connection.execute(
            """
            SELECT r.id, r.tmdb_id, r.media_type, r.rating, r.review_text,
                   r.contains_spoilers, r.watched_at, r.created_at,
                   u.id AS user_id, u.username, u.display_name
            FROM reviews r JOIN users u ON u.id = r.user_id
            WHERE r.user_id = ? OR r.user_id IN (
                SELECT CASE WHEN user_id = ? THEN friend_id ELSE user_id END
                FROM friendships
                WHERE status = 'accepted' AND (user_id = ? OR friend_id = ?)
            )
            ORDER BY r.created_at DESC, r.id DESC LIMIT 50
            """,
            (session["user_id"], session["user_id"], session["user_id"], session["user_id"]),
        ).fetchall()
    finally:
        connection.close()
    return jsonify({"reviews": [dict(row) for row in rows]})


@api.post("/recommendations/rank")
def recommendations_rank():
    payload = request.get_json(silent=True) or {}
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return jsonify({"error": "candidates must be a non-empty list"}), 400

    try:
        ranked = [title.as_dict() for title in rank_candidates(candidates)]
    except (KeyError, TypeError, ValueError) as error:
        return jsonify({"error": f"invalid candidate: {error}"}), 400
    return jsonify({"results": ranked})


def register_api(app):
    init_db(app.config.get("DINNERCUE_DATABASE_PATH"))
    app.register_blueprint(api)


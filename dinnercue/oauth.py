import re

from authlib.integrations.flask_client import OAuth
from flask import redirect, session, url_for

from .db import connect


def _available_username(connection, email, google_sub):
    base = re.sub(r"[^a-z0-9_]", "", email.split("@", 1)[0].lower())[:24] or "moviefan"
    candidate = base
    suffix = 1
    while connection.execute("SELECT 1 FROM users WHERE username = ?", (candidate,)).fetchone():
        suffix += 1
        candidate = f"{base[:20]}_{suffix}"
    return candidate


def register_google_oauth(app):
    oauth = OAuth(app)
    google = oauth.register(
        name="google",
        client_id=app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    app.extensions["dinnercue_google_oauth"] = google

    @app.get("/auth/google")
    def google_login():
        if not app.config.get("GOOGLE_CLIENT_ID") or not app.config.get("GOOGLE_CLIENT_SECRET"):
            return redirect("/?auth=google-unavailable")
        callback = url_for("google_callback", _external=True)
        return google.authorize_redirect(callback)

    @app.get("/auth/google/callback")
    def google_callback():
        token = google.authorize_access_token()
        userinfo = token.get("userinfo") or google.userinfo(token=token)
        google_sub = str(userinfo["sub"])
        email = str(userinfo.get("email", "")).strip().lower()
        display_name = str(userinfo.get("name") or email.split("@", 1)[0] or "Movie fan")[:80]

        connection = connect(app.config.get("DINNERCUE_DATABASE_PATH"))
        try:
            user = connection.execute("SELECT * FROM users WHERE google_sub = ?", (google_sub,)).fetchone()
            if user:
                connection.execute(
                    "UPDATE users SET display_name = ?, email = ?, avatar_url = ? WHERE id = ?",
                    (display_name, email, userinfo.get("picture"), user["id"]),
                )
                user_id = user["id"]
            else:
                cursor = connection.execute(
                    "INSERT INTO users (username, display_name, google_sub, email, avatar_url) VALUES (?, ?, ?, ?, ?)",
                    (_available_username(connection, email, google_sub), display_name, google_sub, email, userinfo.get("picture")),
                )
                user_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()

        session.clear()
        session["user_id"] = user_id
        return redirect("/?auth=google-success")

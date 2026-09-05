from flask import Blueprint, jsonify, request

from .db import init_db
from .recommendations import rank_candidates


api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


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
    init_db()
    app.register_blueprint(api)


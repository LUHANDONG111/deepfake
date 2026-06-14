import base64
import hashlib
import hmac
import json
import time
from functools import wraps

from flask import current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db


def hash_password(password):
    return generate_password_hash(password)


def verify_password(user, password):
    return check_password_hash(user.password_hash, password)


def create_token(user):
    now = int(time.time())
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + int(current_app.config["JWT_EXPIRES_SECONDS"]),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{_b64_json(header)}.{_b64_json(payload)}"
    signature = _sign(signing_input)
    return f"{signing_input}.{signature}"


def decode_token(token):
    try:
        header_b64, payload_b64, signature = token.split(".", 2)
    except ValueError:
        return None

    signing_input = f"{header_b64}.{payload_b64}"
    if not hmac.compare_digest(_sign(signing_input), signature):
        return None

    try:
        payload = json.loads(_b64_decode(payload_b64))
    except (TypeError, ValueError):
        return None

    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def current_user():
    return getattr(g, "current_user", None)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = _load_request_user()
        if user is None:
            return jsonify({"status": "error", "message": "authentication required"}), 401
        if not user.is_active:
            return jsonify({"status": "error", "message": "user is disabled"}), 403
        g.current_user = user
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user().role not in {"admin", "super_admin"}:
            return jsonify({"status": "error", "message": "admin permission required"}), 403
        return view(*args, **kwargs)

    return wrapped


def user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _load_request_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    payload = decode_token(auth_header.removeprefix("Bearer ").strip())
    if not payload:
        return None
    return db.session.get(User, payload.get("sub"))


def _b64_json(value):
    return _b64_encode(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _b64_encode(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(value):
    secret = current_app.config["JWT_SECRET_KEY"].encode("utf-8")
    digest = hmac.new(secret, value.encode("utf-8"), hashlib.sha256).digest()
    return _b64_encode(digest)

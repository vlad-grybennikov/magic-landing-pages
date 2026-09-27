from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException

from settings import Settings

LOCAL_USER = {"id": "local", "email": "local@mlp", "name": "Local", "picture": None}


class AuthError(HTTPException):
    def __init__(self, message: str, status: int = 401):
        super().__init__(status_code=status, detail={"stage": "auth", "message": message})


class UserStore:
    def __init__(self, collection):
        self._users = collection

    def ensure_indexes(self) -> None:
        self._users.create_index("email", unique=True)

    def upsert_google(self, payload: dict) -> dict:
        now = datetime.now(timezone.utc)
        self._users.update_one(
            {"email": payload["email"]},
            {
                "$set": {
                    "email": payload["email"],
                    "google_id": payload.get("sub"),
                    "name": payload.get("name"),
                    "picture": payload.get("picture"),
                    "seen": now,
                },
                "$setOnInsert": {"_id": uuid.uuid4().hex[:16], "created": now},
            },
            upsert=True,
        )
        return self.by_email(payload["email"])

    def by_email(self, email: str) -> Optional[dict]:
        return _public(self._users.find_one({"email": email}))

    def get(self, user_id: str) -> Optional[dict]:
        return _public(self._users.find_one({"_id": user_id}))


def _public(doc: Optional[dict]) -> Optional[dict]:
    if doc is None:
        return None
    return {
        "id": doc["_id"],
        "email": doc.get("email"),
        "name": doc.get("name"),
        "picture": doc.get("picture"),
    }


def bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


class Authenticator:
    def __init__(self, settings: Settings, users: UserStore, verifier=None):
        self.settings = settings
        self.users = users
        self._verify = verifier or _google_verifier(settings.google_client_id)

    @property
    def enabled(self) -> bool:
        return self.settings.auth_enabled

    @property
    def mode(self) -> str:
        return self.settings.env

    def verify_google(self, credential: str) -> dict:
        try:
            payload = self._verify(credential)
        except ValueError as e:
            raise AuthError(f"That Google sign-in could not be verified ({e}).") from e

        if not payload.get("email") or not payload.get("email_verified"):
            raise AuthError("That Google account has no verified email address.")
        return payload

    def sign_in(self, credential: str) -> dict:
        user = self.users.upsert_google(self.verify_google(credential))
        return {"user": user, **self.issue_tokens(user["id"])}

    def refresh(self, refresh_token: str) -> dict:
        user_id = self.user_id_from(refresh_token, "refresh")
        if self.users.get(user_id) is None:
            raise AuthError("That account no longer exists.")
        return self.issue_tokens(user_id)

    def issue_tokens(self, user_id: str) -> dict:
        return {
            "accessToken": self._sign(user_id, "access",
                                      timedelta(minutes=self.settings.access_ttl_min)),
            "refreshToken": self._sign(user_id, "refresh",
                                       timedelta(days=self.settings.refresh_ttl_days)),
        }

    def _sign(self, user_id: str, kind: str, ttl: timedelta) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {"sub": user_id, "kind": kind, "iat": now, "exp": now + ttl},
            self.settings.jwt_secret,
            algorithm="HS256",
        )

    def user_id_from(self, token: str, kind: str = "access") -> str:
        try:
            claims = jwt.decode(token, self.settings.jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as e:
            raise AuthError("Your session has expired -- sign in again.") from e
        except jwt.InvalidTokenError as e:
            raise AuthError("That session token isn't valid.") from e

        if claims.get("kind") != kind:
            raise AuthError(f"Expected a {kind} token.")
        return claims["sub"]

    def authenticate(self, authorization: Optional[str]) -> dict:
        if not self.enabled:
            return LOCAL_USER

        token = bearer(authorization)
        if token is None:
            raise AuthError("Sign in to use the builder.")

        user = self.users.get(self.user_id_from(token))
        if user is None:
            raise AuthError("That account no longer exists.")
        return user


def _google_verifier(client_id: str):
    def verify(credential: str) -> dict:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        return google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), client_id)

    return verify

"""
Google OAuth 2.0 authentication for BillCheck.

Provides:
  - /auth/login        → redirects user to Google consent screen
  - /auth/callback     → Google redirects back here with an auth code
  - /auth/logout       → clears the session cookie
  - /auth/me           → returns the currently logged-in user info
  - get_current_user() → FastAPI dependency to protect routes

Configuration (environment variables):
  GOOGLE_CLIENT_ID      – from Google Cloud Console (APIs & Services → Credentials)
  GOOGLE_CLIENT_SECRET  – same place
  APP_SECRET_KEY        – random string for signing session cookies
  OAUTH_REDIRECT_URI    – defaults to http://localhost:8000/auth/callback

All free — Google OAuth has no usage charges.
"""

from __future__ import annotations

import os
import json
import secrets
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from itsdangerous import URLSafeTimedSerializer

# ── Configuration ────────────────────────────────────────────────────────────

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", secrets.token_urlsafe(32))
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")

# ── OAuth client setup ───────────────────────────────────────────────────────

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# ── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/auth", tags=["auth"])


def _oauth_configured() -> bool:
    """Check whether Google OAuth credentials are set."""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


@router.get("/login")
async def login(request: Request):
    """Redirect the user to Google's OAuth consent screen."""
    if not _oauth_configured():
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars.",
        )
    return await oauth.google.authorize_redirect(request, OAUTH_REDIRECT_URI)


@router.get("/callback")
async def auth_callback(request: Request):
    """Handle the redirect back from Google after consent."""
    if not _oauth_configured():
        raise HTTPException(status_code=503, detail="OAuth not configured")

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"OAuth error: {e}")

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=401, detail="Could not retrieve user info from Google")

    # Store user in session
    request.session["user"] = {
        "email": user_info.get("email", ""),
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
    }

    return RedirectResponse(url="/")


@router.get("/logout")
async def logout(request: Request):
    """Clear the session and redirect to home."""
    request.session.clear()
    return RedirectResponse(url="/")


@router.get("/me")
async def me(request: Request):
    """Return the current user's info, or 401 if not logged in."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": user, "authenticated": True}


@router.get("/status")
async def auth_status(request: Request):
    """Check if OAuth is configured and if the user is logged in."""
    user = request.session.get("user")
    return {
        "oauth_configured": _oauth_configured(),
        "authenticated": user is not None,
        "user": user,
    }


# ── Dependency for protecting routes ─────────────────────────────────────────

async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency: returns the logged-in user dict or raises 401.

    Usage:
        @app.get("/api/protected")
        async def protected(user: dict = Depends(get_current_user)):
            ...

    When OAuth is NOT configured (no env vars), this dependency passes
    through without requiring auth — so the app still works in dev mode.
    """
    if not _oauth_configured():
        # Dev mode: no OAuth configured, allow all requests
        return {"email": "dev@localhost", "name": "Dev User", "picture": ""}

    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in at /auth/login")
    return user

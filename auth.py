"""Auth module — Google OAuth2 with signed session cookies."""
import json
import traceback
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from itsdangerous import URLSafeSerializer, BadSignature

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY
from database import get_or_create_user, get_user_by_id

# ── OAuth Setup ─────────────────────────────────────────────
oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# ── Session Signer ──────────────────────────────────────────
signer = URLSafeSerializer(SECRET_KEY)
COOKIE_NAME = "session_user"

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session(response: Response, user_id: int):
    """Set signed session cookie."""
    token = signer.dumps({"uid": user_id})
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/",
    )


def _get_session(request: Request) -> dict | None:
    """Read and verify signed session cookie."""
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return None
    try:
        return signer.loads(cookie)
    except BadSignature:
        return None


# ── Auth Dependency ─────────────────────────────────────────

async def require_auth(request: Request) -> dict:
    """Dependency that returns the current authenticated user or raises 401."""
    session = _get_session(request)
    if not session:
        raise HTTPException(401, "Not authenticated")
    user = get_user_by_id(session["uid"])
    if not user:
        raise HTTPException(401, "User not found")
    return user


async def optional_auth(request: Request) -> dict | None:
    """Dependency that returns user if logged in, None otherwise."""
    session = _get_session(request)
    if not session:
        return None
    return get_user_by_id(session.get("uid"))


# ── Routes ──────────────────────────────────────────────────

@router.get("/login")
async def login(request: Request):
    """Redirect to Google OAuth2."""
    redirect_uri = str(request.url_for("auth_callback"))
    # Handle proxied requests (Cloudflare tunnel)
    if request.headers.get("x-forwarded-proto") == "https":
        redirect_uri = redirect_uri.replace("http://", "https://")
    print(f"[AUTH] Redirecting to Google with callback: {redirect_uri}")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth2 callback."""
    try:
        print(f"[AUTH] Callback hit, query: {request.query_params}")
        token = await oauth.google.authorize_access_token(request)
        print(f"[AUTH] Token received: {list(token.keys())}")
    except Exception as e:
        print(f"[AUTH ERROR] authorize_access_token failed: {e}")
        traceback.print_exc()
        return RedirectResponse(url="/login?error=oauth_failed")

    user_info = token.get("userinfo")
    if not user_info:
        # Try to decode the id_token manually
        try:
            user_info = token.get("id_token")
            if isinstance(user_info, dict):
                pass  # already decoded
            else:
                # Try parsing the token
                import jwt
                user_info = jwt.decode(token["id_token"], options={"verify_signature": False})
        except Exception:
            pass

    if not user_info:
        print(f"[AUTH ERROR] No userinfo in token. Keys: {list(token.keys())}")
        return RedirectResponse(url="/login?error=no_userinfo")

    print(f"[AUTH] User: {user_info.get('email')}")

    # Get or create user in DB
    user = get_or_create_user(
        email=user_info["email"],
        name=user_info.get("name"),
        picture=user_info.get("picture"),
    )

    # Set session cookie and redirect to app
    response = RedirectResponse(url="/", status_code=302)
    _set_session(response, user["id"])
    return response


@router.get("/me")
async def get_me(user: dict = Depends(require_auth)):
    """Return current user info (without sensitive data)."""
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user["picture"],
        "has_api_key": bool(user["encrypted_api_key"]),
        "theme": user["theme_preference"] or "light",
        "has_seen_tutorial": bool(user["has_seen_tutorial"]),
    }


@router.get("/logout")
async def logout():
    """Clear session cookie."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response

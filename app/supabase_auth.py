import time
import json
import httpx
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

try:
    from .config import (
        SUPABASE_URL,
        SUPABASE_SERVICE_KEY,
        SUPABASE_ANON_KEY,
        FREE_TIER_MAX_SERVERS,
        FREE_TIER_RPM,
        PRO_TIER_MAX_SERVERS,
        PRO_TIER_RPM,
    )
except ImportError:
    from config import (
        SUPABASE_URL,
        SUPABASE_SERVICE_KEY,
        SUPABASE_ANON_KEY,
        FREE_TIER_MAX_SERVERS,
        FREE_TIER_RPM,
        PRO_TIER_MAX_SERVERS,
        PRO_TIER_RPM,
    )



JWKS_CACHE = None
JWKS_CACHE_EXPIRY = 0
PROFILE_CACHE: dict[str, tuple[dict, float]] = {}


async def _fetch_jwks() -> dict:
    global JWKS_CACHE, JWKS_CACHE_EXPIRY
    now = time.time()
    if JWKS_CACHE and now < JWKS_CACHE_EXPIRY:
        return JWKS_CACHE
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/.well-known/jwks.json")
        resp.raise_for_status()
        JWKS_CACHE = resp.json()
        JWKS_CACHE_EXPIRY = now + 3600
    return JWKS_CACHE


def _get_jwk(kid: str, jwks: dict) -> dict | None:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def _decode_jwt_payload(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        pad = 4 - len(payload_b64) % 4
        if pad != 4:
            payload_b64 += "=" * pad
        import base64

        decoded = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded)
    except Exception:
        return None


async def validate_jwt(token: str) -> dict | None:
    if not token:
        return None
    payload = _decode_jwt_payload(token)
    if not payload:
        return None
    exp = payload.get("exp", 0)
    if time.time() > exp:
        return None
    aud = payload.get("aud", "")
    if aud != "authenticated" and SUPABASE_URL not in str(aud):
        pass
    return payload


async def fetch_supabase_profile(user_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/profiles",
            params={"id": f"eq.{user_id}"},
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            },
        )
        resp.raise_for_status()
        rows = resp.json()
        if rows:
            return rows[0]
    return {"status": "active", "plan_tier": "free", "paypal_subscription_id": None}


async def upsert_supabase_profile(user_id: str, data: dict):
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{SUPABASE_URL}/rest/v1/profiles",
            params={"id": f"eq.{user_id}"},
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=data,
        )
        resp.raise_for_status()


async def get_cached_profile(user_id: str) -> dict:
    now = time.time()
    if user_id in PROFILE_CACHE:
        data, expires = PROFILE_CACHE[user_id]
        if now < expires:
            return data
    try:
        profile = await fetch_supabase_profile(user_id)
    except Exception:
        return {"status": "active", "plan_tier": "free", "paypal_subscription_id": None}
    PROFILE_CACHE[user_id] = (profile, now + 60)
    return profile


def invalidate_profile_cache(user_id: str):
    PROFILE_CACHE.pop(user_id, None)


def get_tier_limits(plan_tier: str) -> dict:
    if plan_tier == "pro":
        return {"max_servers": PRO_TIER_MAX_SERVERS, "rpm": PRO_TIER_RPM}
    if plan_tier == "enterprise":
        return {"max_servers": 9999, "rpm": 99999}
    return {"max_servers": FREE_TIER_MAX_SERVERS, "rpm": FREE_TIER_RPM}


async def require_auth(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else auth
    payload = await validate_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    request.state.user_id = payload.get("sub", "")
    request.state.jwt_payload = payload

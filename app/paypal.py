import json
import httpx
from .config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_WEBHOOK_ID, PAYPAL_API_URL


_paypal_token: str | None = None
_paypal_token_expiry: float = 0


async def _get_paypal_token() -> str:
    global _paypal_token, _paypal_token_expiry
    import time

    now = time.time()
    if _paypal_token and now < _paypal_token_expiry:
        return _paypal_token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_API_URL}/v1/oauth2/token",
            headers={"Accept": "application/json"},
            data={"grant_type": "client_credentials"},
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
        )
        resp.raise_for_status()
        data = resp.json()
        _paypal_token = data["access_token"]
        _paypal_token_expiry = now + data.get("expires_in", 30000) - 60
    return _paypal_token


async def verify_webhook_signature(headers: dict, body: bytes) -> bool:
    if not PAYPAL_WEBHOOK_ID:
        return True
    token = await _get_paypal_token()
    verification_data = {
        "auth_algo": headers.get("paypal-auth-algo", ""),
        "cert_url": headers.get("paypal-cert-url", ""),
        "transmission_id": headers.get("paypal-transmission-id", ""),
        "transmission_sig": headers.get("paypal-transmission-sig", ""),
        "transmission_time": headers.get("paypal-transmission-time", ""),
        "webhook_id": PAYPAL_WEBHOOK_ID,
        "webhook_event": json.loads(body.decode()),
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_API_URL}/v1/notifications/verify-webhook-signature",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json=verification_data,
        )
        if resp.status_code != 200:
            return False
        result = resp.json()
        return result.get("verification_status") == "SUCCESS"


EVENT_MAP = {
    "BILLING.SUBSCRIPTION.ACTIVATED": "activated",
    "BILLING.SUBSCRIPTION.PAYMENT.FAILED": "payment_failed",
    "BILLING.SUBSCRIPTION.CANCELLED": "cancelled",
    "BILLING.SUBSCRIPTION.RE-ACTIVATED": "reactivated",
}


def parse_webhook_event(body: bytes) -> dict | None:
    try:
        event = json.loads(body.decode())
        event_type = event.get("event_type", "")
        action = EVENT_MAP.get(event_type)
        if not action:
            return None
        resource = event.get("resource", {})
        custom_id = resource.get("custom_id", "")
        subscription_id = resource.get("id", "")
        return {
            "action": action,
            "event_type": event_type,
            "custom_id": custom_id,
            "subscription_id": subscription_id,
            "raw": event,
        }
    except (json.JSONDecodeError, KeyError):
        return None

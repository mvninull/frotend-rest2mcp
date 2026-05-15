import os


SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID", "")
PAYPAL_PRO_PLAN_ID = os.getenv("PAYPAL_PRO_PLAN_ID", "")
PAYPAL_API_URL = os.getenv("PAYPAL_API_URL", "https://api-m.sandbox.paypal.com")
PAYPAL_SANDBOX = os.getenv("PAYPAL_SANDBOX", "true").lower() == "true"

GATEWAY_HOST = os.getenv("GATEWAY_HOST", "0.0.0.0")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8080"))
PUBLIC_URL = os.getenv("PUBLIC_URL", f"http://localhost:{GATEWAY_PORT}")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cloud.db")

FREE_TIER_MAX_SERVERS = int(os.getenv("FREE_TIER_MAX_SERVERS", "1"))
FREE_TIER_RPM = int(os.getenv("FREE_TIER_RPM", "10"))
PRO_TIER_MAX_SERVERS = int(os.getenv("PRO_TIER_MAX_SERVERS", "10"))
PRO_TIER_RPM = int(os.getenv("PRO_TIER_RPM", "100"))

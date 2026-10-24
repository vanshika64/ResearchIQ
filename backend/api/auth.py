from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from core.settings import settings

bearer = HTTPBearer()

def current_user(token: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        return client.auth.get_user(token.credentials).user.id
    except Exception as exc:
        message = str(exc).lower()
        if "getaddrinfo" in message or "connect" in message or "name resolution" in message:
            raise HTTPException(status_code=503, detail="The backend cannot reach Supabase Auth. Check SUPABASE_URL, DNS, and network/proxy access.") from exc
        raise HTTPException(status_code=401, detail="Invalid or expired Supabase session. Sign in again.") from exc

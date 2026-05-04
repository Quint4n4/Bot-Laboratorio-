"""
auth.py — Validación de tokens HMAC para magic link
El bot ARIA genera tokens con make_token(); el dashboard los valida con verify_token().
"""
import hmac
import hashlib
import os
import time


def _secret() -> str:
    s = os.getenv("DASHBOARD_SECRET", "").strip().strip('"').strip("'")
    if not s:
        raise RuntimeError("DASHBOARD_SECRET no configurado")
    return s


def make_token(telegram_id: str, ttl_hours: int = 24) -> str:
    """
    Genera un token firmado para un usuario.
    Formato: <telegram_id>:<expires_unix>:<hmac_sha256>
    """
    expires = int(time.time()) + ttl_hours * 3600
    payload = f"{telegram_id}:{expires}"
    sig = hmac.new(_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_token(token: str) -> str | None:
    """
    Valida un token. Devuelve telegram_id si es válido, None si no.
    Resistente a tampering por HMAC y a replay tras ttl.
    """
    if not token or token.count(":") != 2:
        return None
    try:
        payload, sig = token.rsplit(":", 1)
        expected = hmac.new(_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        telegram_id, expires_str = payload.split(":")
        if int(expires_str) < int(time.time()):
            return None
        return telegram_id
    except (ValueError, AttributeError):
        return None

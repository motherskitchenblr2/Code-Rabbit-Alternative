# =============================================================================
# Minimal TOTP (RFC 6238) — stdlib only
# =============================================================================
# HMAC-SHA1 time-based one-time password with a 30-second period and 6-digit
# codes, matching Google Authenticator / Authy / 1Password defaults. Kept
# dependency-free (no pyotp/qrcode) to preserve the backend's stdlib-only goal.
# =============================================================================

import base64
import hashlib
import hmac
import os
import struct
import time
from typing import Optional
from urllib.parse import quote_plus

_DIGITS = 6
_PERIOD = 30


def generate_secret(num_bytes: int = 20) -> str:
    """Return a base32 secret (default 32 chars, like pyotp's random_base32)."""
    return base64.b32encode(os.urandom(num_bytes)).decode("ascii").rstrip("=")


def _b32_decode(secret: str) -> bytes:
    pad = (8 - len(secret) % 8) % 8
    return base64.b32decode(secret.upper() + "=" * pad, casefold=True)


def _hotp(secret: str, counter: int) -> int:
    msg = struct.pack(">Q", counter)
    digest = hmac.new(_b32_decode(secret), msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return binary % (10 ** _DIGITS)


def verify_code(secret: str, code: object, window: int = 1) -> bool:
    """True if `code` matches the current (or ±window) TOTP step."""
    if not secret or code is None:
        return False
    try:
        digits = int(str(code).strip())
    except (TypeError, ValueError):
        return False
    step = int(time.time()) // _PERIOD
    for counter in range(step - window, step + window + 1):
        if _hotp(secret, counter) == digits:
            return True
    return False


def current_code(secret: str) -> str:
    """Return the live 6-digit code for `secret` (used by tests and tween flows)."""
    return "%0*d" % (_DIGITS, _hotp(secret, int(time.time()) // _PERIOD))


def otpauth_uri(secret: str, label: str = "Git-Fix Admin", issuer: str = "Git-Fix") -> str:
    return (
        f"otpauth://totp/{quote_plus(label)}"
        f"?secret={secret}&issuer={quote_plus(issuer)}"
        f"&algorithm=SHA1&digits={_DIGITS}&period={_PERIOD}"
    )
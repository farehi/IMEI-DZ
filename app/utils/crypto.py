import os
import base64
from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        # Derive a stable key from SECRET_KEY for development only
        secret = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
        # Fernet needs 32 url-safe base64-encoded bytes
        raw = secret.encode("utf-8")
        padded = (raw + b"0" * 32)[:32]
        key = base64.urlsafe_b64encode(padded)
    else:
        key = key.encode("utf-8") if isinstance(key, str) else key
    return Fernet(key)


def encrypt_text(plain: str) -> str:
    if not plain:
        return ""
    f = _get_fernet()
    return f.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_text(cipher: str) -> str:
    if not cipher:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(cipher.encode("utf-8")).decode("utf-8")
    except Exception:
        return "[مشفر / غير قابل للقراءة]"

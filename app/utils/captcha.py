import random
import hmac
import hashlib
import time
from flask import current_app


def generate_captcha() -> tuple[str, str]:
    """
    Returns (question, token).
    Token = HMAC(answer + timestamp) so we don't store session data.
    """
    a = random.randint(1, 12)
    b = random.randint(1, 12)
    op = random.choice(["+", "-"])
    if op == "+":
        answer = a + b
        question = f"{a} + {b} = ?"
    else:
        if a < b:
            a, b = b, a
        answer = a - b
        question = f"{a} - {b} = ?"

    ts = str(int(time.time()))
    secret = current_app.config["SECRET_KEY"]
    payload = f"{answer}:{ts}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    token = f"{ts}:{sig}"
    return question, token


def verify_captcha(user_answer: str, token: str, max_age: int = 600) -> bool:
    if not user_answer or not token:
        return False
    try:
        answer = int(str(user_answer).strip())
    except ValueError:
        return False

    parts = token.split(":")
    if len(parts) != 2:
        return False
    ts, sig = parts
    try:
        ts_int = int(ts)
    except ValueError:
        return False

    if abs(int(time.time()) - ts_int) > max_age:
        return False

    secret = current_app.config["SECRET_KEY"]
    payload = f"{answer}:{ts}"
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(expected, sig)

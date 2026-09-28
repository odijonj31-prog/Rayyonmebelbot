import hashlib
import hmac
from urllib.parse import parse_qsl

from config import BOT_TOKEN


def validate_init_data(init_data: str) -> dict | None:
    """
    Telegram Mini App yuborgan initData satrini tekshiradi.
    To'g'ri bo'lsa, ichidagi foydalanuvchi ma'lumotlarini (dict) qaytaradi.
    Noto'g'ri yoki soxta bo'lsa, None qaytaradi.
    """
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    return parsed

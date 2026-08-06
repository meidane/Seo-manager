"""رمزنگاری متقارن برای پسورد دسترسی‌ها با cryptography.Fernet.

کلید از `settings.FERNET_KEY` خوانده می‌شود؛ اگر خالی باشد، از `SECRET_KEY`
مشتق می‌شود (فقط برای توسعه — در تولید یک کلید پایدار در .env بگذار، وگرنه با
تغییر SECRET_KEY همه‌ی پسوردها غیرقابل‌بازگشایی می‌شوند).
"""
import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings

_fernet = None


def _build_key() -> bytes:
    key = settings.FERNET_KEY
    if key:
        return key.encode() if isinstance(key, str) else key
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_build_key())
    return _fernet


def encrypt(text: str) -> str:
    if text is None:
        text = ''
    return get_fernet().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    if not token:
        return ''
    return get_fernet().decrypt(token.encode()).decode()

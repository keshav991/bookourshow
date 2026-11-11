import hashlib
import hmac
import string


def razorpay_signature_matches(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def razorpay_webhook_signature_matches(body: bytes, signature: str, secret: str) -> bool:
    if len(signature) != 64 or any(character not in string.hexdigits for character in signature):
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

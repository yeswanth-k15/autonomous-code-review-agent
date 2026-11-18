
import hashlib
import hmac
import os

from dotenv import load_dotenv

load_dotenv()


def verify_github_signature(
    payload_body: bytes,
    signature_header: str | None,
) -> bool:
    """
    Verify the HMAC-SHA256 signature sent by GitHub.
    """

    webhook_secret = os.getenv("WEBHOOK_SECRET")

    if not webhook_secret or not signature_header:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected_signature = "sha256=" + hmac.new(
        webhook_secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        signature_header,
    )

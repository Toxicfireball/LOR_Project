import requests
from django.conf import settings

class EmailSendError(RuntimeError):
    pass

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class EmailSendError(RuntimeError):
    pass

def send_verification_email(user, email, *, verify_url: str) -> str:
    api_key = getattr(settings, "RESEND_API_KEY", "")
    if not api_key:
        raise EmailSendError("RESEND_API_KEY not set")

    from_addr = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    if not from_addr:
        raise EmailSendError("DEFAULT_FROM_EMAIL not configured")

    subject = "Confirm your email address"
    text = (
        f"Hello {user.get_username()},\n\n"
        f"Please confirm your email by clicking this link:\n"
        f"{verify_url}\n\n"
        "If you did not request this, ignore this email.\n"
    )
    html = f"""
      <p>Hello {user.get_username()},</p>
      <p>Please confirm your email by clicking this link:</p>
      <p><a href="{verify_url}">{verify_url}</a></p>
      <p>If you did not request this, ignore this email.</p>
    """

    payload = {
        "from": from_addr,
        "to": [email],
        "subject": subject,
        "text": text,
        "html": html,
    }

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
    except requests.RequestException as e:
        logger.exception("Resend network error sending verification email")
        raise EmailSendError(f"Network error sending verification email: {e!s}")

    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text}

    logger.warning(
        "verification_email status=%s to=%s from=%s response=%s",
        r.status_code,
        email,
        from_addr,
        data,
    )

    if r.status_code // 100 != 2:
        msg = data.get("message") or data.get("error") or r.text or f"HTTP {r.status_code}"
        raise EmailSendError(f"Resend API error: {msg}")

    return data.get("id", "")

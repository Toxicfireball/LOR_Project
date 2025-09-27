import requests
from django.conf import settings

class EmailSendError(RuntimeError):
    pass

def send_verification_email(user, email, *, verify_url: str) -> str:
    """
    Sends a verification email via Resend and returns the message id.
    Raises EmailSendError with a human-friendly message on failure.
    """
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
        "from": from_addr,            # must be a verified domain in Resend
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
            json=payload,   # ← send JSON properly
            timeout=30,
        )
    except requests.RequestException as e:
        raise EmailSendError(f"Network error sending email: {e!s}")

    # Resend normally returns 200 and {'id': '...'} on success.
    if r.status_code // 100 != 2:
        # surface Resend's error body if present
        try:
            data = r.json()
        except Exception:
            data = {"error": r.text}
        msg = data.get("message") or data.get("error") or f"HTTP {r.status_code}"
        raise EmailSendError(f"Resend API error: {msg}")

    try:
        msg_id = r.json().get("id") or ""
    except Exception:
        msg_id = ""

    return msg_id

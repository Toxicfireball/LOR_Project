import json, requests
from django.conf import settings

def send_verification_email(user, email, *, verify_url):
    api_key = settings.RESEND_API_KEY
    if not api_key:
        raise RuntimeError("RESEND_API_KEY not set")

    payload = {
        "from": settings.DEFAULT_FROM_EMAIL,   # no-reply@lorbuilder.com (verified domain)
        "to": [email],
        "subject": "Confirm your email address",
        "html": f"""
          <p>Hello {user.get_username()},</p>
          <p>Please confirm your email by clicking this link:</p>
          <p><a href="{verify_url}">{verify_url}</a></p>
          <p>If you did not request this, ignore this email.</p>
        """,
    }

    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=30,
    )
    r.raise_for_status()

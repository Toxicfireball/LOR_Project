# accounts/email_backends.py
import requests
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

class ResendEmailBackend(BaseEmailBackend):
    api_url = "https://api.resend.com/emails"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "RESEND_API_KEY", "")
        if not api_key:
            if self.fail_silently:
                return 0
            raise Exception("RESEND_API_KEY not set")

        sent = 0
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        for msg in email_messages:
            try:
                html_body = None
                if isinstance(msg, EmailMultiAlternatives):
                    for alt, mimetype in msg.alternatives:
                        if mimetype == "text/html":
                            html_body = alt
                            break

                payload = {
                    "from": msg.from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
                    "to": list(msg.to or []),
                    "cc": list(msg.cc or []),
                    "bcc": list(msg.bcc or []),
                    "subject": msg.subject or "",
                    "text": msg.body or "",
                }
                if html_body:
                    payload["html"] = html_body

                r = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
                if r.status_code // 100 != 2:
                    if not self.fail_silently:
                        try:
                            data = r.json()
                            message = data.get("message") or data.get("error") or r.text
                        except Exception:
                            message = r.text
                        raise Exception(f"Resend API error: {message}")
                    continue
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent

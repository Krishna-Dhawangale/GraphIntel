"""
Email Service — GraphIntel
Handles sending password reset emails via SMTP (async-safe).
Falls back to console logging when EMAIL_ENABLED=False (default dev mode).
"""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from app.core.config import settings

logger = logging.getLogger("graphintel.email")


def _build_reset_email(to_email: str, reset_url: str, full_name: str | None) -> MIMEMultipart:
    name = full_name or "User"
    html_name = escape(name)
    html_reset_url = escape(reset_url, quote=True)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Your GraphIntel Password"
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg["To"] = to_email

    plain = f"""Hi {name},

You requested a password reset for your GraphIntel account.

Click the link below to set a new password (valid for 30 minutes):

{reset_url}

If you did not request this, please ignore this email — your account is safe.

— The GraphIntel Team
"""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#0f0c29;font-family:'Inter',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0c29;padding:40px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0"
             style="background:linear-gradient(135deg,#1a1a3e,#12122a);
                    border:1px solid #2a2a5a;border-radius:16px;overflow:hidden;">
        <!-- Header -->
        <tr>
          <td style="padding:32px 40px 24px;background:linear-gradient(135deg,#6366f1,#8b5cf6);text-align:center;">
            <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;letter-spacing:-0.5px;">
              🔐 Reset Your Password
            </h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:13px;">GraphIntel Market Intelligence Platform</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:32px 40px;">
            <p style="margin:0 0 16px;color:#c7c7e2;font-size:15px;line-height:1.6;">
              Hi <strong style="color:#fff;">{html_name}</strong>,
            </p>
            <p style="margin:0 0 24px;color:#9898c0;font-size:14px;line-height:1.7;">
              We received a request to reset the password for your GraphIntel account.
              Click the button below to set a new password. This link expires in
              <strong style="color:#a78bfa;">30 minutes</strong>.
            </p>
            <!-- CTA Button -->
            <div style="text-align:center;margin:28px 0;">
              <a href="{html_reset_url}"
                 style="display:inline-block;padding:14px 36px;
                        background:linear-gradient(135deg,#6366f1,#8b5cf6);
                        color:#fff;text-decoration:none;border-radius:10px;
                        font-size:15px;font-weight:600;letter-spacing:0.3px;
                        box-shadow:0 4px 20px rgba(99,102,241,0.4);">
                Reset Password
              </a>
            </div>
            <p style="margin:0 0 8px;color:#6060a0;font-size:12px;line-height:1.6;">
              Or copy this link into your browser:
            </p>
            <p style="margin:0 0 24px;word-break:break-all;
                      color:#818cf8;font-size:12px;font-family:monospace;
                      background:#1e1e4a;padding:10px 14px;border-radius:8px;
                      border:1px solid #2a2a6a;">
              {html_reset_url}
            </p>
            <p style="margin:0;color:#6060a0;font-size:12px;line-height:1.6;">
              If you didn't request a password reset, you can safely ignore this email.
              Your account remains secure.
            </p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:16px 40px 24px;border-top:1px solid #2a2a5a;text-align:center;">
            <p style="margin:0;color:#404070;font-size:11px;">
              © 2025 GraphIntel · Market Intelligence Platform
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def send_password_reset_email(to_email: str, reset_token: str, full_name: str | None = None) -> bool:
    """
    Send a password-reset email.

    Returns True on success, False on failure.
    When EMAIL_ENABLED=False, logs the reset URL to console instead (dev mode).
    """
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    if not settings.EMAIL_ENABLED:
        # Dev-mode: print to console so the flow can still be tested
        logger.warning(
            "EMAIL_ENABLED=False — password reset link (console-only):\n"
            f"  To:  {to_email}\n"
            f"  URL: {reset_url}"
        )
        return True  # Treat as success so the endpoint returns 200

    try:
        msg = _build_reset_email(to_email, reset_url, full_name)
        context = ssl.create_default_context()

        if settings.SMTP_TLS:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAILS_FROM_EMAIL, to_email, msg.as_string())
        else:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAILS_FROM_EMAIL, to_email, msg.as_string())

        logger.info(f"Password reset email sent to {to_email}")
        return True

    except Exception as exc:
        logger.error(f"Failed to send password reset email to {to_email}: {exc}")
        return False

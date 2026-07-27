from __future__ import annotations

import logging
import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from typing import Any

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailAdapterInterface(ABC):
    """Abstract base class for email notification transport adapters."""

    @abstractmethod
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Sends an email notification to recipient."""


class MockEmailAdapter(EmailAdapterInterface):
    """In-memory mock email adapter for testing and local dev."""

    def __init__(self) -> None:
        self.sent_emails: list[dict[str, Any]] = []

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        record = {"to_email": to_email, "subject": subject, "body": body}
        self.sent_emails.append(record)
        logger.info(
            "MockEmailAdapter: Email captured for %s with subject '%s'", to_email, subject
        )
        return True

    def clear(self) -> None:
        self.sent_emails.clear()


class SMTPEmailAdapter(EmailAdapterInterface):
    """SMTP email adapter with secret isolation and fallback safety."""

    def __init__(self, settings: Settings) -> None:
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.username = settings.smtp_user
        self.password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.use_tls = settings.smtp_use_tls

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_email, [to_email], msg.as_string())
            logger.info("SMTPEmailAdapter: Sent email to %s", to_email)
            return True
        except Exception:
            logger.exception("SMTPEmailAdapter: Failed to send email to %s", to_email)
            return False


_mock_adapter_instance: MockEmailAdapter | None = None


def get_email_adapter(settings: Settings | None = None) -> EmailAdapterInterface:
    global _mock_adapter_instance
    cfg = settings or get_settings()

    if cfg.email_adapter_mode == "smtp" and cfg.smtp_enabled:
        return SMTPEmailAdapter(cfg)

    if _mock_adapter_instance is None:
        _mock_adapter_instance = MockEmailAdapter()
    return _mock_adapter_instance

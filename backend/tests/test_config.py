from pydantic import ValidationError

from app.core.config import Settings


def test_settings_rejects_invalid_request_size() -> None:
    try:
        Settings(
            database_url="postgresql+psycopg://user:pass@localhost:5432/spip",
            max_request_body_bytes=0,
        )
    except ValidationError:
        return
    raise AssertionError("Settings must reject an invalid request-size limit")

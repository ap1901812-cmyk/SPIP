from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SPIP API"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"
    allowed_origins: Annotated[list[AnyHttpUrl], NoDecode] = Field(default_factory=list)
    max_request_body_bytes: int = Field(default=1_048_576, ge=1, le=52_428_800)
    database_url: PostgresDsn

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def openapi_url(self) -> str | None:
        return f"{self.api_v1_prefix}/openapi.json" if self.app_env != "production" else None


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""
Configuration loader.
Loads all settings from .env file
using Pydantic for type safety.
"""

from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings, 
    SettingsConfigDict
)


class Settings(BaseSettings):
    """
    Application settings loaded from
    environment variables.
    """

    # ━━━ BOT CONFIG ━━━
    bot_token: str = Field(..., alias="BOT_TOKEN")
    bot_username: str = Field(
        ..., alias="BOT_USERNAME"
    )

    # ━━━ TELEGRAM API ━━━
    api_id: int = Field(..., alias="API_ID")
    api_hash: str = Field(..., alias="API_HASH")

    # ━━━ OWNERS ━━━
    superadmin_ids: str = Field(
        ..., alias="SUPERADMIN_IDS"
    )

    # ━━━ DATABASE ━━━
    database_url: str = Field(
        ..., alias="DATABASE_URL"
    )

    # ━━━ ENCRYPTION ━━━
    encryption_key: str = Field(
        ..., alias="ENCRYPTION_KEY"
    )

    # ━━━ FAMGATEWAY (NEW) ━━━
    fam_api_key: str = Field(
        default="", alias="FAM_API_KEY"
    )
    fam_base_url: str = Field(
        default="https://famgateway.in",
        alias="FAM_BASE_URL"
    )
    fam_daily_auto_limit: float = Field(
        default=5000.0,
        alias="FAM_DAILY_AUTO_LIMIT"
    )

    # ━━━ DEFAULTS ━━━
    default_language: str = Field(
        default="en", alias="DEFAULT_LANGUAGE"
    )
    default_2fa_prefix: str = Field(
        default="ghost_", 
        alias="DEFAULT_2FA_PREFIX"
    )
    low_stock_threshold: int = Field(
        default=5, alias="LOW_STOCK_THRESHOLD"
    )
    session_check_interval: int = Field(
        default=1800, 
        alias="SESSION_CHECK_INTERVAL"
    )
    force_sub_check_interval: int = Field(
        default=3600,
        alias="FORCE_SUB_CHECK_INTERVAL"
    )

    # ━━━ ANTI-SPAM ━━━
    rate_limit_seconds: float = Field(
        default=2.0, alias="RATE_LIMIT_SECONDS"
    )

    # ━━━ LOGGING ━━━
    log_level: str = Field(
        default="INFO", alias="LOG_LEVEL"
    )
    log_file: str = Field(
        default="./data/logs/bot.log",
        alias="LOG_FILE"
    )

    # ━━━ PATHS ━━━
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = base_dir / "data"
    sessions_dir: Path = data_dir / "sessions"
    logs_dir: Path = data_dir / "logs"
    uploads_dir: Path = data_dir / "uploads"
    locales_dir: Path = (
        base_dir / "bot" / "locales"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("superadmin_ids")
    @classmethod
    def validate_admin_ids(
        cls, v: str
    ) -> str:
        """Validate superadmin IDs format."""
        if not v:
            raise ValueError(
                "SUPERADMIN_IDS cannot be empty"
            )
        try:
            ids = [
                int(x.strip()) 
                for x in v.split(",")
            ]
            if not ids:
                raise ValueError
        except ValueError:
            raise ValueError(
                "SUPERADMIN_IDS must be "
                "comma-separated integers"
            )
        return v

    @property
    def superadmin_id_list(self) -> List[int]:
        """Get superadmin IDs as list."""
        return [
            int(x.strip())
            for x in self.superadmin_ids.split(",")
        ]

    def ensure_directories(self) -> None:
        """Create required directories."""
        for dir_path in [
            self.data_dir,
            self.sessions_dir,
            self.logs_dir,
            self.uploads_dir
        ]:
            dir_path.mkdir(
                parents=True, exist_ok=True
            )


# ━━━ SINGLETON INSTANCE ━━━
settings = Settings()
settings.ensure_directories()
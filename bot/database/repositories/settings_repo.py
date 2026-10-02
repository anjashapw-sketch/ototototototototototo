"""Settings repository — key-value store."""

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Setting


class SettingsRepository:
    """Repository for bot settings."""

    # ━━━━━━━━━━━━━━━━━━━
    # GENERAL SETTINGS
    # ━━━━━━━━━━━━━━━━━━━

    KEY_FORCE_SUB = "force_sub_enabled"
    KEY_LOW_STOCK_ALERT = "low_stock_alert"
    KEY_SESSION_CHECK = "session_check_enabled"
    KEY_SALE_NOTIF = "sale_notifications"
    KEY_DAILY_REPORT = "daily_report"
    KEY_BALANCE_REQ_NOTIF = "balance_req_notif"
    KEY_NEW_USER_NOTIF = "new_user_notif"
    KEY_AUTO_2FA = "auto_2fa"
    KEY_LOW_STOCK_THRESHOLD = "low_stock_threshold"

    # ━━━━━━━━━━━━━━━━━━━
    # PAYMENT SETTINGS
    # ━━━━━━━━━━━━━━━━━━━

    KEY_UPI_ID = "upi_id"
    KEY_UPI_QR_FILE_ID = "upi_qr_file_id"
    KEY_USDT_BEP20_ADDRESS = "usdt_bep20_address"
    KEY_USDT_RATE = "usdt_rate"
    KEY_MIN_DEPOSIT = "min_deposit"
    KEY_MAX_DEPOSIT = "max_deposit"

    # ━━━━━━━━━━━━━━━━━━━
    # SUPPORT
    # ━━━━━━━━━━━━━━━━━━━

    KEY_SUPPORT_USERNAME = "support_username"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> Optional[str]:
        """Get setting value."""

        result = await self.session.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else None

    async def get_bool(
        self,
        key: str,
        default: bool = False,
    ) -> bool:
        """Get setting as boolean."""

        value = await self.get(key)
        if value is None:
            return default
        return value.lower() in (
            "true", "1", "yes", "on"
        )

    async def get_int(
        self,
        key: str,
        default: int = 0,
    ) -> int:
        """Get setting as integer."""

        value = await self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    async def get_float(
        self,
        key: str,
        default: float = 0.0,
    ) -> float:
        """Get setting as float."""

        value = await self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    async def set(
        self,
        key: str,
        value: str,
    ) -> None:
        """Set or update setting."""

        existing = await self.get(key)
        if existing is not None:
            await self.session.execute(
                update(Setting)
                .where(Setting.key == key)
                .values(value=value)
            )
        else:
            setting = Setting(key=key, value=value)
            self.session.add(setting)
            await self.session.flush()

    async def set_bool(
        self,
        key: str,
        value: bool,
    ) -> None:
        """Set boolean setting."""

        await self.set(
            key,
            "true" if value else "false",
        )

    async def toggle_bool(
        self,
        key: str,
        default: bool = False,
    ) -> bool:
        """Toggle boolean setting."""

        current = await self.get_bool(key, default)
        new_value = not current
        await self.set_bool(key, new_value)
        return new_value
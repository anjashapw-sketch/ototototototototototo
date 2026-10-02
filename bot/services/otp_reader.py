"""
OTP reader service.
Wraps SessionManager for OTP operations.
"""

from typing import Optional, Tuple

from bot.database.models import Account
from bot.services.encryption import (
    encryption_service
)
from bot.services.fingerprint import (
    DeviceFingerprint
)
from bot.services.session_manager import (
    session_manager
)
from bot.utils.logger import log


class OtpReader:
    """High-level OTP reading interface."""

    @staticmethod
    async def read_otp(
        account: Account
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Read latest OTP for an account.

        Args:
            account: Account model

        Returns:
            (otp_code, full_message)
        """
        # Decrypt session
        session_str = encryption_service.decrypt(
            account.session_string
        )

        if not session_str:
            log.error(
                f"❌ Decrypt failed: "
                f"acc={account.id}"
            )
            return (None, None)

        # Load fingerprint if exists
        fp = None
        if account.device_fingerprint:
            try:
                fp = DeviceFingerprint.from_json(
                    account.device_fingerprint
                )
            except Exception as e:
                log.warning(
                    f"Fingerprint load failed: "
                    f"{e}"
                )

        # Read OTP via session manager
        otp, full_msg = (
            await session_manager
            .read_latest_otp(
                session_string=session_str,
                fingerprint=fp
            )
        )

        return (otp, full_msg)

    @staticmethod
    async def terminate_session(
        account: Account
    ) -> bool:
        """
        Logout bot's session from account.

        Args:
            account: Account model

        Returns:
            True if successful
        """
        session_str = encryption_service.decrypt(
            account.session_string
        )

        if not session_str:
            return False

        fp = None
        if account.device_fingerprint:
            try:
                fp = DeviceFingerprint.from_json(
                    account.device_fingerprint
                )
            except Exception:
                pass

        return (
            await session_manager
            .logout_bot_session(
                session_string=session_str,
                fingerprint=fp
            )
        )

    @staticmethod
    async def check_alive(
        account: Account
    ) -> bool:
        """Check if account session is alive."""
        session_str = encryption_service.decrypt(
            account.session_string
        )

        if not session_str:
            return False

        fp = None
        if account.device_fingerprint:
            try:
                fp = DeviceFingerprint.from_json(
                    account.device_fingerprint
                )
            except Exception:
                pass

        return (
            await session_manager
            .check_session_alive(
                session_string=session_str,
                fingerprint=fp
            )
        )


# ━━━ SINGLETON ━━━
otp_reader = OtpReader()
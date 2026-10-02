"""
Ultra-stealth Pyrogram session manager.
Handles login, OTP, 2FA with maximum
anti-detection measures.
"""

import asyncio
import random
from typing import Optional, Tuple

from pyrogram import Client
from pyrogram.errors import (
    AuthKeyUnregistered,
    FloodWait,
    PasswordHashInvalid,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberInvalid,
    SessionPasswordNeeded,
    Unauthorized,
)

from bot.config import settings
from bot.services.fingerprint import (
    DeviceFingerprint,
    fingerprint_generator,
)
from bot.utils.logger import log


class SessionResult:
    """Result of session operations."""

    def __init__(
        self,
        success: bool,
        message: str = "",
        data: Optional[dict] = None,
    ):
        self.success = success
        self.message = message
        self.data = data or {}

    def __bool__(self) -> bool:
        return self.success


class SessionManager:
    """
    Ultra-stealth session manager.
    Mimics real Telegram client behavior.
    """

    def __init__(self):
        self.api_id = settings.api_id
        self.api_hash = settings.api_hash

    @staticmethod
    async def _human_delay(
        min_s: float = 1.5,
        max_s: float = 4.0,
    ) -> None:
        """
        Add human-like random delay.
        Real users don't make instant requests.
        """
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)

    def _create_client(
        self,
        session_string: Optional[str] = None,
        fingerprint: Optional[
            DeviceFingerprint
        ] = None,
        in_memory: bool = True,
    ) -> Client:
        """
        Create stealth Pyrogram client
        with full device fingerprint.
        """
        if fingerprint is None:
            fingerprint = (
                fingerprint_generator.generate()
            )

        # Unique session name per client
        session_name = (
            f"stealth_{fingerprint.device_id}"
            if fingerprint.device_id
            else f"stealth_{random.randint(1000, 9999)}"
        )

        kwargs = {
            "name": session_name,
            "api_id": self.api_id,
            "api_hash": self.api_hash,
            "in_memory": in_memory,
            "device_model": (
                fingerprint.device_model
            ),
            "system_version": (
                fingerprint.system_version
            ),
            "app_version": (
                fingerprint.app_version
            ),
            "lang_code": fingerprint.lang_code,
            "no_updates": True,
            "sleep_threshold": 30,
        }

        if session_string:
            kwargs["session_string"] = (
                session_string
            )

        return Client(**kwargs)

    async def send_code(
        self,
        phone: str,
        fingerprint: Optional[
            DeviceFingerprint
        ] = None,
    ) -> SessionResult:
        """
        Step 1: Send OTP with stealth measures.
        """
        # Generate phone-specific fingerprint
        if fingerprint is None:
            # Try to detect country for matching lang
            country_code = None
            try:
                from bot.services.country_detector import (
                    country_detector,
                )
                country_code, _ = (
                    country_detector.detect(phone)
                )
            except Exception:
                pass

            fingerprint = (
                fingerprint_generator.generate(
                    country_code=country_code,
                    phone=phone,
                )
            )

        client = self._create_client(
            fingerprint=fingerprint
        )

        try:
            # Human-like delay before action
            await self._human_delay(0.5, 1.5)

            await client.connect()

            # Mimic real client (small pause)
            await self._human_delay(0.8, 2.0)

            sent = await client.send_code(phone)

            log.info(
                f"✅ OTP sent to {phone} "
                f"[{fingerprint.device_model}]"
            )
            return SessionResult(
                success=True,
                message="OTP sent successfully",
                data={
                    "client": client,
                    "phone_code_hash": (
                        sent.phone_code_hash
                    ),
                    "fingerprint": fingerprint,
                },
            )

        except PhoneNumberInvalid:
            await self._safe_disconnect(client)
            return SessionResult(
                success=False,
                message=(
                    "Invalid phone number format"
                ),
            )

        except FloodWait as e:
            await self._safe_disconnect(client)
            return SessionResult(
                success=False,
                message=(
                    f"⏳ Rate limited. "
                    f"Wait {e.value} seconds."
                ),
            )

        except Exception as e:
            await self._safe_disconnect(client)
            log.error(f"❌ send_code failed: {e}")
            return SessionResult(
                success=False,
                message=f"Error: {str(e)[:100]}",
            )

    async def verify_code(
        self,
        client: Client,
        phone: str,
        phone_code_hash: str,
        code: str,
    ) -> SessionResult:
        """
        Step 2: Verify OTP with stealth delays.
        """
        try:
            # Human-like delay (reading OTP)
            await self._human_delay(2.0, 5.0)

            await client.sign_in(
                phone_number=phone,
                phone_code_hash=phone_code_hash,
                phone_code=code,
            )

            # Small post-login delay
            await self._human_delay(1.0, 2.5)

            session_str = (
                await client.export_session_string()
            )

            # Keep session alive briefly (real users
            # don't disconnect instantly)
            await self._human_delay(1.5, 3.0)

            await self._safe_disconnect(client)

            log.info(f"✅ Login OK: {phone}")
            return SessionResult(
                success=True,
                message="Login successful",
                data={
                    "session_string": session_str,
                    "needs_2fa": False,
                },
            )

        except SessionPasswordNeeded:
            log.info(f"🔐 2FA needed: {phone}")
            return SessionResult(
                success=False,
                message="2FA password required",
                data={
                    "client": client,
                    "needs_2fa": True,
                },
            )

        except PhoneCodeInvalid:
            return SessionResult(
                success=False,
                message="❌ Invalid OTP code",
            )

        except PhoneCodeExpired:
            await self._safe_disconnect(client)
            return SessionResult(
                success=False,
                message=(
                    "⏰ OTP expired. Request new."
                ),
            )

        except FloodWait as e:
            await self._safe_disconnect(client)
            return SessionResult(
                success=False,
                message=(
                    f"⏳ Rate limited. "
                    f"Wait {e.value}s."
                ),
            )

        except Exception as e:
            err_str = str(e)
            log.error(
                f"❌ verify_code failed: {err_str}"
            )

            # Handle "incomplete login attempt"
            if "incomplete" in err_str.lower() or (
                "AUTH_RESTART" in err_str.upper()
            ):
                await self._safe_disconnect(client)
                return SessionResult(
                    success=False,
                    message=(
                        "⚠️ Login attempt expired.\n"
                        "Please restart and try again."
                    ),
                )

            await self._safe_disconnect(client)
            return SessionResult(
                success=False,
                message=f"Error: {err_str[:100]}",
            )

    async def verify_2fa(
        self,
        client: Client,
        password: str,
    ) -> SessionResult:
        """
        Step 3: Verify 2FA password.
        """
        try:
            # Human-like delay
            await self._human_delay(2.0, 4.5)

            await client.check_password(password)

            # Post-login delay
            await self._human_delay(1.0, 2.5)

            session_str = (
                await client.export_session_string()
            )

            await self._human_delay(1.5, 3.0)
            await self._safe_disconnect(client)

            log.info("✅ 2FA verified")
            return SessionResult(
                success=True,
                message="Login successful",
                data={
                    "session_string": session_str,
                },
            )

        except PasswordHashInvalid:
            return SessionResult(
                success=False,
                message="❌ Incorrect 2FA password",
            )

        except FloodWait as e:
            await self._safe_disconnect(client)
            return SessionResult(
                success=False,
                message=(
                    f"⏳ Rate limited. "
                    f"Wait {e.value}s."
                ),
            )

        except Exception as e:
            await self._safe_disconnect(client)
            log.error(f"❌ 2FA verify failed: {e}")
            return SessionResult(
                success=False,
                message=f"Error: {str(e)[:100]}",
            )

    async def set_2fa(
        self,
        client: Client,
        new_password: str,
        hint: str = "Account Security",
    ) -> SessionResult:
        """
        Set 2FA password silently.
        """
        try:
            await self._human_delay(2.0, 4.0)

            await client.enable_cloud_password(
                password=new_password,
                hint=hint,
            )

            log.info("✅ 2FA set successfully")
            return SessionResult(
                success=True,
                message="2FA set successfully",
            )
        except Exception as e:
            log.error(f"❌ set_2fa failed: {e}")
            return SessionResult(
                success=False,
                message=f"Error: {str(e)[:100]}",
            )

    async def check_session_alive(
        self,
        session_string: str,
        fingerprint: Optional[
            DeviceFingerprint
        ] = None,
    ) -> bool:
        """Check if session is still alive."""
        client = self._create_client(
            session_string=session_string,
            fingerprint=fingerprint,
        )

        try:
            await client.connect()
            me = await client.get_me()
            await self._safe_disconnect(client)
            return me is not None
        except (
            Unauthorized,
            AuthKeyUnregistered,
        ):
            return False
        except Exception as e:
            log.warning(
                f"Session check error: {e}"
            )
            return False

    async def read_latest_otp(
        self,
        session_string: str,
        fingerprint: Optional[
            DeviceFingerprint
        ] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Read latest Telegram OTP."""
        client = self._create_client(
            session_string=session_string,
            fingerprint=fingerprint,
        )

        try:
            await client.connect()
            await self._human_delay(0.5, 1.5)

            async for msg in client.get_chat_history(
                777000, limit=10
            ):
                if not msg.text:
                    continue

                otp = self._extract_otp(msg.text)
                if otp:
                    await self._safe_disconnect(client)
                    return (otp, msg.text)

            await self._safe_disconnect(client)
            return (None, None)

        except Exception as e:
            log.error(f"❌ OTP read failed: {e}")
            await self._safe_disconnect(client)
            return (None, None)

    @staticmethod
    def _extract_otp(
        text: str,
    ) -> Optional[str]:
        """Extract OTP code from message text."""
        import re

        patterns = [
            r"Login code[:\s]+(\d{4,8})",
            r"code[:\s]+(\d{4,8})",
            r"\b(\d{5,6})\b",
        ]

        for pattern in patterns:
            match = re.search(
                pattern, text, re.IGNORECASE
            )
            if match:
                return match.group(1)
        return None

    async def logout_bot_session(
        self,
        session_string: str,
        fingerprint: Optional[
            DeviceFingerprint
        ] = None,
    ) -> bool:
        """Logout bot session from account."""
        client = self._create_client(
            session_string=session_string,
            fingerprint=fingerprint,
        )

        try:
            await client.connect()
            await self._human_delay(1.0, 2.0)
            await client.log_out()
            log.info("✅ Bot session terminated")
            return True
        except Exception as e:
            log.error(f"❌ Logout failed: {e}")
            await self._safe_disconnect(client)
            return False

    @staticmethod
    async def _safe_disconnect(
        client: Client,
    ) -> None:
        """Safely disconnect client."""
        try:
            if client.is_connected:
                await client.disconnect()
        except Exception:
            pass


# ━━━ SINGLETON INSTANCE ━━━
session_manager = SessionManager()
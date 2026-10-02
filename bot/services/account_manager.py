"""
Account manager service.
Handles account purchase, encryption, etc.
"""

from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Account
from bot.database.repositories import (
    AccountRepository,
    PricingRepository
)
from bot.services.country_detector import (
    country_detector
)
from bot.services.encryption import (
    encryption_service
)
from bot.services.fingerprint import (
    fingerprint_generator
)
from bot.services.wallet_service import (
    WalletService
)
from bot.utils.logger import log


class AccountManager:
    """High-level account operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.acc_repo = AccountRepository(
            session
        )
        self.pricing_repo = PricingRepository(
            session
        )
        self.wallet = WalletService(session)

    async def add_account(
        self,
        phone: str,
        session_string: str,
        twofa_password: str,
        added_by: int,
        custom_price: Optional[Decimal] = None
    ) -> Tuple[bool, str, Optional[Account]]:
        """
        Add new account to stock.

        Returns:
            (success, message, account)
        """
        # Check duplicate
        existing = await self.acc_repo.get_by_phone(
            phone
        )
        if existing:
            return (
                False,
                "Phone number already exists",
                None
            )

        # Detect country
        code, name = country_detector.detect(
            phone
        )

        # Get price
        if custom_price is not None:
            price = custom_price
        else:
            price = (
                await self.pricing_repo.get_price(
                    code
                )
            )

        # Encrypt sensitive data
        encrypted_session = (
            encryption_service.encrypt(
                session_string
            )
        )
        encrypted_2fa = (
            encryption_service.encrypt(
                twofa_password
            )
        )

        # Generate fingerprint
        fp = fingerprint_generator.generate(
            code
        )
        fp_json = fp.to_json()

        # Create account
        try:
            account = await self.acc_repo.create(
                phone=phone,
                country_code=code,
                country_name=name,
                session_string=encrypted_session,
                twofa_password=encrypted_2fa,
                price=price,
                added_by=added_by,
                device_fingerprint=fp_json
            )
            log.info(
                f"✅ Account added: {phone} "
                f"({code})"
            )
            return (
                True,
                "Account added successfully",
                account
            )
        except Exception as e:
            log.error(
                f"❌ Add account failed: {e}"
            )
            return (False, str(e), None)

    async def purchase_account(
        self,
        user_id: int,
        country_code: str
    ) -> Tuple[bool, str, Optional[Account]]:
        """
        Purchase one account for user.

        Returns:
            (success, message, account)
        """
        # Get available account
        account = (
            await self.acc_repo
            .get_available_by_country(
                country_code
            )
        )

        if not account:
            return (
                False,
                "No accounts in stock",
                None
            )

        # Check balance & deduct
        success, msg = await self.wallet.debit(
            user_id=user_id,
            amount=account.price,
            description=(
                f"Purchased "
                f"{account.country_name} "
                f"account: {account.phone}"
            )
        )

        if not success:
            return (False, msg, None)

        # Mark as sold
        try:
            await self.acc_repo.mark_as_sold(
                acc_id=account.id,
                sold_to=user_id
            )
            log.info(
                f"💰 Sold: acc={account.id} "
                f"to user={user_id}"
            )
            return (
                True,
                "Purchase successful",
                account
            )
        except Exception as e:
            # Rollback wallet
            await self.wallet.credit(
                user_id=user_id,
                amount=account.price,
                description=(
                    "Refund: purchase failed"
                )
            )
            log.error(
                f"❌ Sell failed: {e}"
            )
            return (False, str(e), None)

    def decrypt_session(
        self, account: Account
    ) -> Optional[str]:
        """Decrypt session string."""
        return encryption_service.decrypt(
            account.session_string
        )

    def decrypt_2fa(
        self, account: Account
    ) -> Optional[str]:
        """Decrypt 2FA password."""
        return encryption_service.decrypt(
            account.twofa_password
        )
"""
FamGateway integration service.
Handles order creation, status polling, and auto-approval.

Uses the official `famgateway` PyPI SDK.
All SDK calls are synchronous — run in thread executor
to avoid blocking the async event loop.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# ── Try to import SDK; fallback if not installed ──
try:
    from famgateway import FamGateway as FamClient
    _FAM_SDK_AVAILABLE = True
except ImportError:
    FamClient = None
    _FAM_SDK_AVAILABLE = False

from bot.config import settings
from bot.database.engine import get_session
from bot.database.models.wallet_request import (
    PaymentMethod,
    WalletRequest,
    WalletRequestStatus,
)
from bot.database.repositories.wallet_repo import (
    WalletRequestRepository,
)
from bot.utils.logger import log


class FamGatewayService:
    """Async wrapper around the synchronous FamGateway SDK."""

    def __init__(self, session=None):
        self.session = session

        if not _FAM_SDK_AVAILABLE:
            log.error(
                "❌ FamGateway SDK not installed. "
                "Run: pip install famgateway"
            )
            self._client = None
            return

        # ✅ FIXED: lowercase attribute access
        api_key = settings.fam_api_key
        base_url = settings.fam_base_url

        if not api_key:
            log.error(
                "❌ FAM_API_KEY missing in .env / config"
            )
            self._client = None
            return

        try:
            self._client = FamClient(
                api_key=api_key,
                base_url=base_url,
                timeout=15,
            )
        except Exception as e:
            log.error(f"❌ FamGateway init failed: {e}")
            self._client = None

    async def _run_sync(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: fn(*args, **kwargs)
        )

    async def create_order(
        self,
        amount: float,
        customer_name: str | None = None,
        customer_phone: str | None = None,
    ) -> dict:
        """Create a FamGateway order."""
        if not self._client:
            raise RuntimeError(
                "FamGateway client not initialized. "
                "Check logs / .env"
            )

        try:
            order = await self._run_sync(
                self._client.create_order,
                amount=amount,
                customer_name=customer_name,
                customer_phone=customer_phone,
            )
            return {
                "order_id": order.order_id,
                "qr_url": order.qr_url,
                "upi_intent": order.upi_intent,
                "checkout_url": order.checkout_url,
                "payable_amount": float(order.payable_amount),
                "expires_at": getattr(
                    order, "expires_at_ist", None
                ),
            }
        except Exception as e:
            log.error(
                f"❌ FamGateway create_order failed: {e}"
            )
            raise

    async def check_status(self, order_id: str) -> dict:
        """Check payment status via public endpoint."""
        if not self._client:
            return {
                "is_paid": False,
                "is_pending": True,
                "is_expired": False,
                "utr": None,
                "sender_name": None,
            }

        try:
            status = await self._run_sync(
                self._client.get_status, order_id
            )
            return {
                "is_paid": status.is_paid,
                "is_pending": getattr(
                    status, "is_pending", False
                ),
                "is_expired": getattr(
                    status, "is_expired", False
                ),
                "utr": getattr(status, "utr", None),
                "sender_name": getattr(
                    status, "sender_name", None
                ),
            }
        except Exception as e:
            log.error(
                f"❌ FamGateway check_status failed "
                f"for {order_id}: {e}"
            )
            return {
                "is_paid": False,
                "is_pending": True,
                "is_expired": False,
                "utr": None,
                "sender_name": None,
            }

    async def verify_order(self, order_id: str) -> dict:
        """Full server-side verification."""
        if not self._client:
            return {"is_paid": False, "utr": None,
                    "sender_name": None}

        try:
            status = await self._run_sync(
                self._client.verify_order, order_id
            )
            return {
                "is_paid": status.is_paid,
                "utr": getattr(status, "utr", None),
                "sender_name": getattr(
                    status, "sender_name", None
                ),
            }
        except Exception as e:
            log.error(
                f"❌ FamGateway verify_order failed "
                f"for {order_id}: {e}"
            )
            return {"is_paid": False, "utr": None,
                    "sender_name": None}


# ── DB-integrated helpers ──

async def create_fam_wallet_request(
    user_id: int,
    amount_inr: float,
    customer_name: str | None = None,
) -> tuple[WalletRequest, dict]:
    """Create a FamGateway order + DB record."""
    svc = FamGatewayService()

    fam_data = await svc.create_order(
        amount=amount_inr,
        customer_name=customer_name,
    )

    async with get_session() as session:
        repo = WalletRequestRepository(session)
        req = WalletRequest(
            user_id=user_id,
            amount_inr=Decimal(str(amount_inr)),
            payment_method=PaymentMethod.FAMGATEWAY,
            status=WalletRequestStatus.PENDING,
            fam_order_id=fam_data["order_id"],
            fam_qr_url=fam_data["qr_url"],
            fam_upi_intent=fam_data["upi_intent"],
            fam_checkout_url=fam_data["checkout_url"],
            fam_expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=5),
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)

    return req, fam_data


async def auto_approve_fam_request(
    order_id: str,
    utr: str,
    sender_name: str | None = None,
) -> WalletRequest | None:
    """Auto-approve a FamGateway payment."""
    async with get_session() as session:
        repo = WalletRequestRepository(session)
        req = await repo.get_by_fam_order_id(order_id)

        if not req:
            log.warning(
                f"⚠️ Auto-approve: order {order_id} not found"
            )
            return None

        if req.status != WalletRequestStatus.PENDING:
            return None

        # ✅ FIXED: lowercase access
        daily_limit = settings.fam_daily_auto_limit
        if daily_limit > 0:
            try:
                today_total = (
                    await repo.get_today_auto_approved_amount(
                        req.user_id
                    )
                )
            except AttributeError:
                today_total = 0.0

            if (
                today_total + float(req.amount_inr)
                > daily_limit
            ):
                log.warning(
                    f"⚠️ Auto-approve daily limit exceeded "
                    f"for user {req.user_id}."
                )
                req.admin_note = (
                    "⚠️ Auto-approve daily limit exceeded — "
                    "manual review required."
                )
                await session.commit()
                return req

        # Credit wallet
        from bot.services.wallet_service import WalletService

        wallet_svc = WalletService(session)
        success, msg, _ = await wallet_svc.approve_request(
            request_id=req.id,
            approved_by=0,
            admin_note=(
                f"Auto-verified via FamGateway | "
                f"UTR: {utr} | Payer: {sender_name or 'N/A'}"
            ),
        )

        if not success:
            log.error(
                f"❌ Auto-approve credit failed "
                f"for #{req.id}: {msg}"
            )
            return None

        req.utr_id = utr
        req.fam_utr = utr
        req.fam_sender_name = sender_name
        req.auto_verified = True
        req.status = WalletRequestStatus.AUTO_APPROVED
        await session.commit()
        await session.refresh(req)

    log.info(
        f"✅ Auto-approved FamGateway order {order_id} "
        f"(₹{req.amount_inr}) | UTR: {utr}"
    )
    return req
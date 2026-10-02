"""
Background poller for FamGateway orders.
Checks pending orders every 3 seconds and auto-approves payments.
"""

import asyncio

from bot.config import settings
from bot.database.engine import get_session
from bot.database.repositories.wallet_repo import (
    WalletRequestRepository,
)
from bot.services.famgateway_service import (
    FamGatewayService,
    auto_approve_fam_request,
)
from bot.utils.logger import log

_IN_FLIGHT: set[str] = set()


async def poll_famgateway_orders() -> None:
    """Poll pending FamGateway orders forever."""
    log.info("🔄 FamGateway poller started")
    await asyncio.sleep(5)

    poll_interval = 3

    while True:
        try:
            await _poll_cycle()
        except Exception as e:
            log.error(f"❌ FamGateway poller error: {e}")

        await asyncio.sleep(poll_interval)


async def _poll_cycle() -> None:
    """One polling cycle."""
    async with get_session() as session:
        repo = WalletRequestRepository(session)
        pending = await repo.get_pending_fam_orders()

    if not pending:
        return

    svc = FamGatewayService()

    for req in pending:
        if req.fam_order_id in _IN_FLIGHT:
            continue
        _IN_FLIGHT.add(req.fam_order_id)

        try:
            status = await svc.check_status(req.fam_order_id)

            if status["is_paid"]:
                approved = await auto_approve_fam_request(
                    order_id=req.fam_order_id,
                    utr=status["utr"] or "",
                    sender_name=status["sender_name"],
                )
                if approved and approved.auto_verified:
                    await _notify_auto_approved(approved)

        except Exception as e:
            log.error(
                f"❌ Poll error for {req.fam_order_id}: {e}"
            )
        finally:
            _IN_FLIGHT.discard(req.fam_order_id)

        await asyncio.sleep(0.3)


async def _notify_auto_approved(req) -> None:
    """Notify user + owner on auto-approval."""
    try:
        from bot.loader import bot as _bot
        from bot.database.repositories import UserRepository

        async with get_session() as session:
            user_repo = UserRepository(session)
            db_user = await user_repo.get_by_id(req.user_id)

        if not db_user:
            return

        await _bot.send_message(
            chat_id=db_user.telegram_id,
            text=(
                f"✅ <b>Payment Auto-Verified!</b>\n\n"
                f"💰 ₹{float(req.amount_inr):.2f} "
                f"has been added to your wallet.\n"
                f"🔢 Order: <code>{req.fam_order_id}</code>\n"
                f"🧾 UTR: <code>{req.fam_utr or 'N/A'}</code>"
            ),
        )

        owner_id = getattr(settings, "OWNER_ID", None)
        if owner_id:
            try:
                await _bot.send_message(
                    chat_id=owner_id,
                    text=(
                        f"🔔 <b>Auto-Approved Deposit</b>\n\n"
                        f"👤 User: <code>{req.user_id}</code>\n"
                        f"💰 ₹{float(req.amount_inr):.2f}\n"
                        f"🔢 Order: <code>{req.fam_order_id}</code>"
                    ),
                )
            except Exception:
                pass

    except Exception as e:
        log.error(f"❌ Auto-approve notify failed: {e}")
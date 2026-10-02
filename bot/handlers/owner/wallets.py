"""
Owner wallet handler.
Approve / Reject deposit requests.
Configure UPI (FamGateway) + USDT (BEP20) payment settings.
"""

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.database.engine import get_session
from bot.database.models.wallet_request import (
    PaymentMethod,
    WalletRequestStatus,
)
from bot.database.repositories import UserRepository
from bot.database.repositories.settings_repo import (
    SettingsRepository,
)
from bot.database.repositories.wallet_repo import (
    WalletRequestRepository,
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.owner.confirmations import (
    get_owner_back_kb,
)
from bot.keyboards.owner.main_menu import OWNER_MENU
from bot.keyboards.owner.wallets import (
    get_payment_settings_kb,
    get_pending_requests_kb,
    get_request_action_kb,
    get_wallets_menu_kb,
)
from bot.services.wallet_service import WalletService
from bot.states.settings import SettingsStates
from bot.states.wallet_request import (
    WalletRequestStates,
)
from bot.utils.formatters import (
    format_datetime,
    format_money,
)
from bot.utils.helpers import escape_html
from bot.utils.logger import log

# ── FamGateway imports ──
from bot.services.famgateway_service import (
    FamGatewayService,
    create_fam_wallet_request,
    auto_approve_fam_request,
)

wallets_router = Router(name="owner_wallets")
wallets_router.message.filter(IsOwner())
wallets_router.callback_query.filter(IsOwner())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPER — Smart edit (handles photo+text)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _smart_edit_or_send(
    callback: CallbackQuery,
    text: str,
    reply_markup=None,
) -> None:
    """Edit text/caption or send new message."""
    msg = callback.message

    if msg.photo or msg.video or msg.document:
        try:
            await msg.edit_caption(
                caption=text,
                reply_markup=reply_markup,
            )
            return
        except Exception:
            pass

    try:
        await msg.edit_text(
            text=text,
            reply_markup=reply_markup,
        )
        return
    except Exception:
        pass

    try:
        await msg.delete()
    except Exception:
        pass

    await msg.answer(
        text=text,
        reply_markup=reply_markup,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WALLET MENU (Reply KB + Callback + /cmd)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.message(
    F.text == OWNER_MENU["wallets"]
)
async def msg_wallets_reply(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Handle Wallets reply keyboard button."""
    await state.clear()

    async with get_session() as session:
        req_repo = WalletRequestRepository(session)
        pending_count = await req_repo.get_pending_count()

    text = (
        f"💳 <b>Wallet Management</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"⏳ Pending Requests: <b>{pending_count}</b>\n"
    )

    kb = get_wallets_menu_kb(pending_count)
    await message.answer(text, reply_markup=kb)


@wallets_router.message(F.text == "/wallets")
async def msg_wallets_cmd(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Handle /wallets command."""
    await msg_wallets_reply(message, state, **kwargs)


@wallets_router.callback_query(
    F.data == "owner:wallets"
)
async def cb_wallets_menu(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """Handle wallets callback."""
    async with get_session() as session:
        req_repo = WalletRequestRepository(session)
        pending_count = await req_repo.get_pending_count()

    text = (
        f"💳 <b>Wallet Management</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"⏳ Pending Requests: <b>{pending_count}</b>\n"
    )

    kb = get_wallets_menu_kb(pending_count)
    await _smart_edit_or_send(callback, text, kb)
    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PENDING REQUESTS LIST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data == "owner:wallet_pending"
)
async def cb_pending_requests(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """Show list of pending deposit requests."""

    async with get_session() as session:
        req_repo = WalletRequestRepository(session)
        requests = await req_repo.get_pending(limit=10)

    if not requests:
        await _smart_edit_or_send(
            callback,
            "✅ No pending deposit requests!",
            get_wallets_menu_kb(0),
        )
        await callback.answer()
        return

    text = (
        f"⏳ <b>Pending Requests</b> "
        f"({len(requests)})\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
    )

    for req in requests:
        method = req.payment_method.value.upper()
        text += (
            f"🔢 <code>#{req.id}</code> | "
            f"₹{format_money(req.amount_inr)} | "
            f"{method}\n"
            f"📅 {format_datetime(req.created_at)}\n\n"
        )

    await _smart_edit_or_send(
        callback,
        text,
        get_pending_requests_kb(requests),
    )
    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VIEW SINGLE REQUEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data.startswith("owner:wallet_req:")
)
async def cb_view_request(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """View a single deposit request."""

    request_id = int(callback.data.split(":")[-1])

    async with get_session() as session:
        req_repo = WalletRequestRepository(session)
        req = await req_repo.get_by_id(request_id)

        if not req:
            await callback.answer(
                "❌ Request not found!",
                show_alert=True,
            )
            return

        user_repo = UserRepository(session)
        db_user = await user_repo.get_by_id(
            req.user_id
        )

    # Method label
    if req.payment_method == PaymentMethod.FAMGATEWAY:
        method_label = "💳 UPI (Auto)"
    elif req.payment_method == PaymentMethod.USDT_BEP20:
        method_label = "🪙 USDT BEP20"
    else:
        method_label = "💳 UPI"

    utr_line = (
        f"🔑 UTR: <code>{req.utr_id}</code>\n"
        if req.utr_id else ""
    )

    name = escape_html(
        getattr(db_user, "first_name", None)
        or str(req.user_id)
    )

    text = (
        f"🔢 <b>Request #{request_id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 User: <b>{name}</b>\n"
        f"🆔 DB ID: <code>{req.user_id}</code>\n\n"
        f"💰 Amount: <b>₹{format_money(req.amount_inr)}</b>\n"
        f"📋 Method: <b>{method_label}</b>\n"
        f"{utr_line}"
        f"📅 Date: {format_datetime(req.created_at)}\n"
        f"📊 Status: <b>{req.status.value.upper()}</b>\n"
    )

    kb = get_request_action_kb(request_id)

    if req.screenshot_file_id:
        try:
            await callback.message.answer_photo(
                photo=req.screenshot_file_id,
                caption=text,
                reply_markup=kb,
            )
            await callback.answer()
            return
        except Exception:
            pass

    await _smart_edit_or_send(callback, text, kb)
    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# APPROVE REQUEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data.startswith("owner:wallet_approve:")
)
async def cb_approve_request(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """Approve deposit request and credit wallet."""

    request_id = int(callback.data.split(":")[-1])
    admin_id = callback.from_user.id

    async with get_session() as session:
        wallet_svc = WalletService(session)
        success, msg, req = await wallet_svc.approve_request(
            request_id=request_id,
            approved_by=admin_id,
        )
        await session.commit()

    if not success:
        await callback.answer(
            f"❌ {msg}", show_alert=True
        )
        return

    await _notify_user_approved(req=req)

    await _smart_edit_or_send(
        callback,
        f"✅ <b>Request #{request_id} Approved!</b>\n\n"
        f"💰 ₹{format_money(req.amount_inr)} "
        f"credited to user.",
    )
    await callback.answer(
        "✅ Approved!", show_alert=False
    )

    log.info(
        f"✅ Admin {admin_id} approved "
        f"request #{request_id}"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REJECT REQUEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data.startswith("owner:wallet_reject:")
)
async def cb_reject_request(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Ask for rejection reason."""

    request_id = int(callback.data.split(":")[-1])
    await state.update_data(
        reject_request_id=request_id
    )
    await state.set_state(
        WalletRequestStates.entering_reject_note
    )

    await _smart_edit_or_send(
        callback,
        f"❌ <b>Reject Request #{request_id}</b>\n\n"
        f"Enter rejection reason (or send /skip):",
    )
    await callback.answer()


@wallets_router.message(
    WalletRequestStates.entering_reject_note,
    F.text,
)
async def msg_reject_note(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Process rejection with note."""

    data = await state.get_data()
    request_id = data.get("reject_request_id")
    admin_id = message.from_user.id

    note = (
        None
        if message.text.strip() == "/skip"
        else message.text.strip()
    )

    await state.clear()

    async with get_session() as session:
        wallet_svc = WalletService(session)
        success, msg, req = await wallet_svc.reject_request(
            request_id=request_id,
            rejected_by=admin_id,
            admin_note=note,
        )
        await session.commit()

    if not success:
        await message.answer(f"❌ {msg}")
        return

    await _notify_user_rejected(req=req, note=note)

    await message.answer(
        f"❌ <b>Request #{request_id} Rejected!</b>\n"
        f"Note: {note or 'None'}",
    )

    log.info(
        f"❌ Admin {admin_id} rejected "
        f"request #{request_id}"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAYMENT SETTINGS MENU (UPI + USDT)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data == "owner:payment_settings"
)
async def cb_payment_settings(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """Show payment settings — UPI + USDT."""

    from datetime import datetime

    async with get_session() as session:
        settings = SettingsRepository(session)

        # UPI
        fam_auto = await settings.get(
            "fam_auto_enabled"
        ) or "true"
        fam_limit = await settings.get_float(
            "fam_daily_limit", default=5000.0
        )

        # USDT
        usdt_addr = await settings.get(
            "usdt_bep20_address"
        ) or ""
        usdt_rate_mode = await settings.get(
            "usdt_rate_mode"
        ) or "auto"
        usdt_rate_manual = await settings.get_float(
            "usdt_rate", default=83.0
        )
        usdt_rate_live = await settings.get_float(
            "usdt_rate_live", default=0
        )
        last_update = await settings.get(
            "usdt_rate_last_update"
        )

        # Common
        min_dep = await settings.get_float(
            SettingsRepository.KEY_MIN_DEPOSIT,
            default=10.0,
        )
        max_dep = await settings.get_float(
            SettingsRepository.KEY_MAX_DEPOSIT,
            default=100000.0,
        )

    # USDT address display
    if not usdt_addr:
        addr_display = "⚠️ <b>NOT SET</b>"
    elif len(usdt_addr) > 15:
        addr_display = (
            f"<code>{usdt_addr[:8]}...{usdt_addr[-6:]}</code>"
        )
    else:
        addr_display = f"<code>{usdt_addr}</code>"

    # Rate display
    if usdt_rate_mode == "auto":
        if usdt_rate_live > 0:
            rate_display = (
                f"🔄 Auto: <b>₹{usdt_rate_live:.2f}</b>"
            )
            if last_update:
                try:
                    dt = datetime.fromisoformat(
                        last_update
                    )
                    rate_display += (
                        f" <i>({dt.strftime('%H:%M')})</i>"
                    )
                except Exception:
                    pass
        else:
            rate_display = "🔄 Auto: <i>tap refresh</i>"
    else:
        rate_display = (
            f"✏️ Manual: <b>₹{usdt_rate_manual:.2f}</b>"
        )

    text = (
        f"⚙️ <b>Payment Settings</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>UPI (FamGateway)</b>\n"
        f"  Auto-Verify: "
        f"<b>{'✅ ON' if fam_auto == 'true' else '❌ OFF'}</b>\n"
        f"  Daily Limit: <b>₹{fam_limit}</b>\n\n"
        f"🪙 <b>USDT BEP20</b>\n"
        f"  Address: {addr_display}\n"
        f"  Rate: {rate_display}\n\n"
        f"📊 <b>Common</b>\n"
        f"  Min Deposit: <b>₹{min_dep}</b>\n"
        f"  Max Deposit: <b>₹{max_dep}</b>"
    )

    await _smart_edit_or_send(
        callback,
        text,
        get_payment_settings_kb(),
    )
    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USDT — SET ADDRESS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data == "owner:set_usdt_address"
)
async def cb_set_usdt_address(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Ask for USDT BEP20 address."""
    await state.set_state(
        SettingsStates.waiting_usdt_address
    )

    await _smart_edit_or_send(
        callback,
        "🪙 <b>Set USDT BEP20 Address</b>\n\n"
        "Send your BEP20 wallet address:\n"
        "Example: <code>0xABC123DEF456...</code>\n\n"
        "⚠️ Make sure it's <b>BEP20 (BSC)</b> network!",
        get_owner_back_kb("owner:payment_settings"),
    )
    await callback.answer()


@wallets_router.message(
    SettingsStates.waiting_usdt_address,
    F.text,
)
async def msg_set_usdt_address(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Save USDT address."""
    address = message.text.strip()

    if len(address) < 20:
        await message.answer(
            "❌ Invalid address (min 20 chars).\n"
            "BEP20 address starts with <code>0x</code>"
        )
        return

    async with get_session() as session:
        repo = SettingsRepository(session)
        await repo.set("usdt_bep20_address", address)

    await state.clear()

    await message.answer(
        f"✅ <b>USDT Address Saved!</b>\n\n"
        f"<code>{address}</code>\n\n"
        f"Users can now deposit via USDT BEP20.",
        reply_markup=get_owner_back_kb(
            "owner:payment_settings"
        ),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USDT — RATE MODE TOGGLE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data == "owner:toggle_usdt_rate_mode"
)
async def cb_toggle_usdt_rate_mode(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """Toggle auto/manual rate mode."""

    async with get_session() as session:
        repo = SettingsRepository(session)
        current = await repo.get(
            "usdt_rate_mode"
        ) or "auto"
        new_mode = "manual" if current == "auto" else "auto"
        await repo.set("usdt_rate_mode", new_mode)

    icon = "🔄" if new_mode == "auto" else "✏️"
    await callback.answer(
        f"{icon} Rate mode: {new_mode.upper()}",
        show_alert=True,
    )
    await cb_payment_settings(callback)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USDT — SET MANUAL RATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data == "owner:set_usdt_rate"
)
async def cb_set_usdt_rate(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Ask for manual USDT rate."""
    await state.set_state(
        SettingsStates.waiting_usdt_rate
    )

    await _smart_edit_or_send(
        callback,
        "📊 <b>Set Manual USDT Rate</b>\n\n"
        "Enter INR value for 1 USDT:\n"
        "Example: <code>83</code>\n\n"
        "⚠️ This will be used when Rate Mode is "
        "<b>Manual</b>.",
        get_owner_back_kb("owner:payment_settings"),
    )
    await callback.answer()


@wallets_router.message(
    SettingsStates.waiting_usdt_rate,
    F.text,
)
async def msg_set_usdt_rate(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Save manual USDT rate."""
    text = message.text.strip()

    try:
        value = float(text)
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Invalid rate.")
        return

    async with get_session() as session:
        repo = SettingsRepository(session)
        await repo.set("usdt_rate", str(value))

    await state.clear()

    await message.answer(
        f"✅ Manual rate set: <code>₹{value}/USDT</code>",
        reply_markup=get_owner_back_kb(
            "owner:payment_settings"
        ),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USDT — REFRESH LIVE RATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data == "owner:refresh_live_rate"
)
async def cb_refresh_live_rate(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """Manually refresh live rate."""

    from bot.services.rate_service import (
        refresh_rate_cache,
    )

    await callback.answer("⏳ Fetching live rate...")

    try:
        await refresh_rate_cache()

        async with get_session() as session:
            repo = SettingsRepository(session)
            live = await repo.get_float(
                "usdt_rate_live", default=0
            )

        await callback.answer(
            f"✅ Live rate: ₹{live:.2f}/USDT",
            show_alert=True,
        )
    except Exception as e:
        log.error(f"❌ Rate refresh failed: {e}")
        await callback.answer(
            f"❌ Failed: {e}",
            show_alert=True,
        )

    await cb_payment_settings(callback)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FAMGATEWAY — VIEW PENDING ORDERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data == "owner:fam_pending"
)
async def cb_fam_pending(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """Show FamGateway orders that need attention."""

    async with get_session() as session:
        req_repo = WalletRequestRepository(session)
        pending = await req_repo.get_pending_fam_orders(
            limit=20
        )

    if not pending:
        await _smart_edit_or_send(
            callback,
            "✅ No pending FamGateway orders!",
        )
        await callback.answer()
        return

    text = (
        f"🔄 <b>FamGateway Pending Orders</b> "
        f"({len(pending)})\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
    )

    kb_rows = []
    for req in pending:
        text += (
            f"🔢 <code>{req.fam_order_id}</code>\n"
            f"💰 ₹{float(req.amount_inr):.2f} | "
            f"👤 {req.user_id}\n"
            f"📅 {format_datetime(req.created_at)}\n\n"
        )
        kb_rows.append([
            InlineKeyboardButton(
                text=f"✅ Verify #{req.fam_order_id}",
                callback_data=(
                    f"owner:fam_manual_verify:"
                    f"{req.fam_order_id}"
                ),
            ),
        ])

    kb_rows.append([
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="owner:wallets",
        ),
    ])

    await _smart_edit_or_send(
        callback,
        text,
        InlineKeyboardMarkup(inline_keyboard=kb_rows),
    )
    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FAMGATEWAY — MANUAL VERIFY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data.startswith("owner:fam_manual_verify:")
)
async def cb_fam_manual_verify(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """
    Manually verify a FamGateway order.
    Use only if auto-poller missed it.
    """
    order_id = callback.data.split(":")[-1]
    admin_id = callback.from_user.id

    svc = FamGatewayService()
    status = await svc.verify_order(order_id)

    if not status["is_paid"]:
        await callback.answer(
            "❌ Payment not found on FamGateway. "
            "Wait 10-15 seconds and try again.",
            show_alert=True,
        )
        return

    approved = await auto_approve_fam_request(
        order_id=order_id,
        utr=status["utr"],
        sender_name=status["sender_name"],
    )

    if not approved:
        await callback.answer(
            "⚠️ Already processed or not found in DB.",
            show_alert=True,
        )
        return

    await _notify_auto_approved(approved)

    await _smart_edit_or_send(
        callback,
        f"✅ <b>FamGateway Order Verified!</b>\n\n"
        f"🔢 Order: <code>{order_id}</code>\n"
        f"🧾 UTR: <code>{status['utr']}</code>\n"
        f"💰 ₹{float(approved.amount_inr):.2f} credited.\n\n"
        f"<i>Manually verified by admin "
        f"{admin_id}.</i>",
    )
    await callback.answer("✅ Verified!")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SET MIN DEPOSIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data == "owner:set_min_deposit"
)
async def cb_set_min_deposit(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Ask for min deposit."""
    await state.set_state(
        SettingsStates.waiting_min_deposit
    )

    await _smart_edit_or_send(
        callback,
        "📉 <b>Set Minimum Deposit (INR)</b>\n\n"
        "Send the minimum deposit amount:\n"
        "Example: <code>10</code>",
        get_owner_back_kb("owner:payment_settings"),
    )
    await callback.answer()


@wallets_router.message(
    SettingsStates.waiting_min_deposit,
    F.text,
)
async def msg_set_min_deposit(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Save min deposit."""
    text = message.text.strip()

    try:
        value = float(text)
        if value < 1:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid amount (min 1)."
        )
        return

    async with get_session() as session:
        repo = SettingsRepository(session)
        await repo.set(
            repo.KEY_MIN_DEPOSIT,
            str(value),
        )

    await state.clear()

    await message.answer(
        f"✅ Min deposit set: <code>₹{value}</code>",
        reply_markup=get_owner_back_kb(
            "owner:payment_settings"
        ),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SET MAX DEPOSIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data == "owner:set_max_deposit"
)
async def cb_set_max_deposit(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Ask for max deposit."""
    await state.set_state(
        SettingsStates.waiting_max_deposit
    )

    await _smart_edit_or_send(
        callback,
        "📈 <b>Set Maximum Deposit (INR)</b>\n\n"
        "Send the maximum deposit amount:\n"
        "Example: <code>100000</code>",
        get_owner_back_kb("owner:payment_settings"),
    )
    await callback.answer()


@wallets_router.message(
    SettingsStates.waiting_max_deposit,
    F.text,
)
async def msg_set_max_deposit(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Save max deposit."""
    text = message.text.strip()

    try:
        value = float(text)
        if value < 1:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid amount (min 1)."
        )
        return

    async with get_session() as session:
        repo = SettingsRepository(session)
        await repo.set(
            repo.KEY_MAX_DEPOSIT,
            str(value),
        )

    await state.clear()

    await message.answer(
        f"✅ Max deposit set: <code>₹{value}</code>",
        reply_markup=get_owner_back_kb(
            "owner:payment_settings"
        ),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SET FAMGATEWAY AUTO-VERIFY ON/OFF
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data == "owner:toggle_fam_auto"
)
async def cb_toggle_fam_auto(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """Toggle FamGateway auto-verification."""

    async with get_session() as session:
        repo = SettingsRepository(session)
        current = await repo.get(
            "fam_auto_enabled"
        ) or "true"
        new_val = "false" if current == "true" else "true"
        await repo.set("fam_auto_enabled", new_val)

    label = "✅ ON" if new_val == "true" else "❌ OFF"
    await callback.answer(
        f"Auto-verify: {label}", show_alert=True
    )
    await cb_payment_settings(callback)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SET FAMGATEWAY DAILY AUTO-LIMIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallets_router.callback_query(
    F.data == "owner:set_fam_daily_limit"
)
async def cb_set_fam_daily_limit(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Ask for daily auto-limit."""
    await state.set_state(
        SettingsStates.waiting_fam_daily_limit
    )

    await _smart_edit_or_send(
        callback,
        "🛡️ <b>Set UPI Daily Auto-Limit (INR)</b>\n\n"
        "Max amount auto-approved per user per day.\n"
        "Example: <code>5000</code>\n"
        "(Set 0 for unlimited)",
        get_owner_back_kb("owner:payment_settings"),
    )
    await callback.answer()


@wallets_router.message(
    SettingsStates.waiting_fam_daily_limit,
    F.text,
)
async def msg_set_fam_daily_limit(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Save daily auto-limit."""
    text = message.text.strip()

    try:
        value = float(text)
        if value < 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid amount (min 0)."
        )
        return

    async with get_session() as session:
        repo = SettingsRepository(session)
        await repo.set(
            "fam_daily_limit",
            str(value),
        )

    await state.clear()

    await message.answer(
        f"✅ Daily auto-limit set: "
        f"<code>₹{value}</code>",
        reply_markup=get_owner_back_kb(
            "owner:payment_settings"
        ),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USER NOTIFICATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _notify_user_approved(req) -> None:
    """Notify user their deposit was approved."""

    try:
        from bot.loader import bot as _bot

        async with get_session() as session:
            user_repo = UserRepository(session)
            db_user = await user_repo.get_by_id(
                req.user_id
            )

        if not db_user:
            return

        await _bot.send_message(
            chat_id=db_user.telegram_id,
            text=(
                f"✅ <b>Deposit Approved!</b>\n\n"
                f"💰 ₹{format_money(req.amount_inr)} "
                f"has been added to your wallet.\n"
                f"🔢 Request: <code>#{req.id}</code>"
            ),
        )
    except Exception as e:
        log.error(f"❌ User notify failed: {e}")


async def _notify_user_rejected(
    req,
    note: str | None,
) -> None:
    """Notify user their deposit was rejected."""

    try:
        from bot.loader import bot as _bot

        async with get_session() as session:
            user_repo = UserRepository(session)
            db_user = await user_repo.get_by_id(
                req.user_id
            )

        if not db_user:
            return

        note_line = (
            f"\n📝 Reason: {note}" if note else ""
        )

        await _bot.send_message(
            chat_id=db_user.telegram_id,
            text=(
                f"❌ <b>Deposit Rejected</b>\n\n"
                f"Your deposit request "
                f"<code>#{req.id}</code> "
                f"has been rejected.{note_line}\n\n"
                f"Contact support if you think "
                f"this is a mistake."
            ),
        )
    except Exception as e:
        log.error(f"❌ User notify failed: {e}")


async def _notify_auto_approved(req) -> None:
    """Notify user + owner about auto-approval."""
    try:
        from bot.loader import bot as _bot
        from bot.config import settings

        async with get_session() as session:
            user_repo = UserRepository(session)
            db_user = await user_repo.get_by_id(
                req.user_id
            )

        if not db_user:
            return

        # User notification
        await _bot.send_message(
            chat_id=db_user.telegram_id,
            text=(
                f"✅ <b>Payment Auto-Verified!</b>\n\n"
                f"💰 ₹{float(req.amount_inr):.2f} "
                f"has been added to your wallet.\n"
                f"🔢 Order: <code>{req.fam_order_id}</code>\n"
                f"🧾 UTR: <code>{req.fam_utr}</code>\n"
                f"👤 Payer: "
                f"{req.fam_sender_name or 'N/A'}\n\n"
                f"<i>Credited automatically "
                f"via FamGateway.</i>"
            ),
        )

        # Owner notification
        owner_id = getattr(settings, "OWNER_ID", None)
        if owner_id:
            try:
                await _bot.send_message(
                    chat_id=owner_id,
                    text=(
                        f"🔔 <b>Auto-Approved Deposit</b>\n\n"
                        f"👤 User: <code>{req.user_id}</code>\n"
                        f"💰 ₹{float(req.amount_inr):.2f}\n"
                        f"🔢 Order: "
                        f"<code>{req.fam_order_id}</code>\n"
                        f"🧾 UTR: <code>{req.fam_utr}</code>\n"
                        f"📊 Status: AUTO_APPROVED"
                    ),
                )
            except Exception:
                pass

    except Exception as e:
        log.error(f"❌ Auto-approve notify failed: {e}")
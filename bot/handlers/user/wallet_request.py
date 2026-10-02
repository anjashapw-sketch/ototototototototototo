"""
Wallet deposit request handler.
Supports UPI (FamGateway auto) + USDT (BEP20 manual).
Flow:
  - UPI: amount → QR → auto-verify (3-5 sec)
  - USDT: amount → address + rate → screenshot → admin approve
"""

from decimal import Decimal, InvalidOperation

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
)
from bot.database.repositories import UserRepository
from bot.database.repositories.settings_repo import (
    SettingsRepository,
)
from bot.database.repositories.wallet_repo import (
    WalletRequestRepository,
)
from bot.keyboards.user.wallet import get_cancel_kb
from bot.keyboards.user.common import (
    get_back_menu_kb,
)
from bot.services.famgateway_service import (
    FamGatewayService,
    create_fam_wallet_request,
    auto_approve_fam_request,
)
from bot.services.notification import (
    notification_service,
)
from bot.states.wallet_request import (
    WalletRequestStates,
)
from bot.utils.formatters import format_money
from bot.utils.helpers import escape_html
from bot.utils.logger import log

wallet_request_router = Router(
    name="wallet_request"
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPER — Finalize message (remove buttons)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _finalize_message(
    callback: CallbackQuery,
    new_caption: str,
) -> None:
    """Remove inline buttons + update caption."""
    msg = callback.message

    try:
        await msg.edit_reply_markup(reply_markup=None)
    except Exception as e:
        log.warning(f"⚠️ Remove keyboard failed: {e}")

    if msg.photo:
        try:
            await msg.edit_caption(
                caption=new_caption,
                reply_markup=None,
            )
            return
        except Exception as e:
            log.warning(f"⚠️ Edit caption failed: {e}")

    try:
        await msg.edit_text(
            text=new_caption,
            reply_markup=None,
        )
        return
    except Exception:
        pass

    try:
        await msg.answer(new_caption)
    except Exception as e:
        log.error(f"❌ Finalize message failed: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1 — METHOD CHOOSER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallet_request_router.callback_query(
    F.data == "wallet:deposit"
)
async def cb_start_deposit(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """Show payment method chooser."""

    await state.clear()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 UPI (Instant Auto)",
                    callback_data="wallet:deposit_upi",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🪙 Crypto (USDT BEP20)",
                    callback_data="wallet:deposit_crypto",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="wallet:cancel_request",
                ),
            ],
        ]
    )

    text = (
        f"💰 <b>Add Balance</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Choose payment method:</b>\n\n"
        f"💳 <b>UPI</b> — Instant auto-verify\n"
        f"<i>PhonePe, GPay, Paytm, FamPay</i>\n\n"
        f"🪙 <b>USDT BEP20</b> — Crypto\n"
        f"<i>Manual verify (5-30 min)</i>"
    )

    try:
        await callback.message.edit_text(
            text, reply_markup=kb
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb
        )
    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UPI FLOW — STEP 1
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallet_request_router.callback_query(
    F.data == "wallet:deposit_upi"
)
async def cb_deposit_upi(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """Start UPI auto flow — ask amount."""

    await state.update_data(
        payment_method=PaymentMethod.FAMGATEWAY.value
    )

    async with get_session() as session:
        settings = SettingsRepository(session)
        min_dep = await settings.get_float(
            SettingsRepository.KEY_MIN_DEPOSIT,
            default=10.0,
        )
        max_dep = await settings.get_float(
            SettingsRepository.KEY_MAX_DEPOSIT,
            default=100000.0,
        )

    await state.set_state(
        WalletRequestStates.entering_fam_amount
    )

    await callback.message.edit_text(
        f"💳 <b>UPI Payment</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Enter amount in <b>INR</b>:\n\n"
        f"📉 Min: <b>₹{min_dep}</b>\n"
        f"📈 Max: <b>₹{max_dep}</b>\n\n"
        f"⚡ <i>Payment auto-verifies within "
        f"3-5 seconds.</i>\n\n"
        f"Send the amount you want to deposit:",
        reply_markup=get_cancel_kb(),
    )
    await callback.answer()


@wallet_request_router.message(
    WalletRequestStates.entering_fam_amount,
)
async def msg_enter_fam_amount(
    message: Message,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """Validate amount → create FamGateway order → send QR."""

    if not message.text:
        await message.answer(
            "❌ Please send a number.",
            reply_markup=get_cancel_kb(),
        )
        return

    text_input = message.text.strip()
    if text_input.lower() in ("/cancel", "cancel"):
        await state.clear()
        await message.answer(
            "❌ Deposit cancelled.",
            reply_markup=get_back_menu_kb(lang),
        )
        return

    try:
        amount = Decimal(
            text_input.replace(",", "")
        )
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer(
            "❌ Invalid amount.\n"
            "Example: <code>100</code>",
            reply_markup=get_cancel_kb(),
        )
        return

    async with get_session() as session:
        settings = SettingsRepository(session)
        min_dep = Decimal(
            str(await settings.get_float(
                SettingsRepository.KEY_MIN_DEPOSIT,
                default=10.0,
            ))
        )
        max_dep = Decimal(
            str(await settings.get_float(
                SettingsRepository.KEY_MAX_DEPOSIT,
                default=100000.0,
            ))
        )
        user_repo = UserRepository(session)
        db_user = await user_repo.get_by_telegram_id(
            message.from_user.id
        )

    if not db_user:
        await message.answer(
            "❌ User not found. Send /start first."
        )
        return

    if amount < min_dep or amount > max_dep:
        await message.answer(
            f"❌ Amount must be between "
            f"<b>₹{min_dep}</b> and "
            f"<b>₹{max_dep}</b>.",
            reply_markup=get_cancel_kb(),
        )
        return

    await state.clear()

    loading = await message.answer(
        "⏳ Creating payment order..."
    )

    try:
        req, fam_data = await create_fam_wallet_request(
            user_id=db_user.id,
            amount_inr=float(amount),
            customer_name=(
                f"{message.from_user.first_name} "
                f"({message.from_user.id})"
            ),
        )
    except Exception as e:
        log.error(
            f"❌ FamGateway create_order failed: {e}"
        )
        await loading.edit_text(
            "❌ Failed to create order. Try again later."
        )
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 Open Payment Page",
                    url=fam_data["checkout_url"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Verify Payment",
                    callback_data=(
                        f"wallet:fam_check:"
                        f"{fam_data['order_id']}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="wallet:cancel_request",
                ),
            ],
        ]
    )

    caption = (
        f"💳 <b>UPI Payment</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Amount: <b>₹{format_money(amount)}</b>\n"
        f"🔢 Order: <code>{fam_data['order_id']}</code>\n\n"
        f"📱 <b>Scan the QR</b> above with any UPI app:\n"
        f"PhonePe • GPay • Paytm • FamPay • BHIM\n\n"
        f"⚡ <i>Auto-verifies within 3-5 seconds "
        f"of payment.</i>\n"
        f"⏰ Order expires in 5 minutes."
    )

    try:
        await loading.delete()
    except Exception:
        pass

    qr_sent = False
    try:
        await message.answer_photo(
            photo=fam_data["qr_url"],
            caption=caption,
            reply_markup=kb,
        )
        qr_sent = True
    except Exception as e:
        log.error(f"❌ QR send failed: {e}")

    if not qr_sent:
        await message.answer(
            caption
            + f"\n\n🔗 <a href='{fam_data['checkout_url']}'>"
            f"Tap here to pay</a>",
            reply_markup=kb,
            disable_web_page_preview=False,
        )

    await _notify_owner_new_order(
        request_id=req.id,
        user=message.from_user,
        amount_inr=amount,
        fam_order_id=fam_data["order_id"],
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USDT FLOW — STEP 1 (Ask Amount)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallet_request_router.callback_query(
    F.data == "wallet:deposit_crypto"
)
async def cb_deposit_crypto(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """Start USDT crypto flow — ask amount in USDT."""

    from bot.services.rate_service import (
        get_usdt_inr_rate,
    )

    await state.update_data(
        payment_method=PaymentMethod.USDT_BEP20.value
    )

    async with get_session() as session:
        settings = SettingsRepository(session)
        min_dep = await settings.get_float(
            SettingsRepository.KEY_MIN_DEPOSIT,
            default=10.0,
        )
        max_dep = await settings.get_float(
            SettingsRepository.KEY_MAX_DEPOSIT,
            default=100000.0,
        )
        usdt_addr = await settings.get(
            "usdt_bep20_address"
        ) or ""

    # ✅ Check: USDT address set hai?
    if not usdt_addr:
        await callback.answer(
            "⚠️ USDT deposit is currently unavailable.\n"
            "Please contact admin or use UPI.",
            show_alert=True,
        )
        return

    # Get live rate
    rate = await get_usdt_inr_rate()

    await state.set_state(
        WalletRequestStates.entering_amount
    )

    min_usdt = min_dep / rate
    max_usdt = max_dep / rate

    await callback.message.edit_text(
        f"🪙 <b>USDT Deposit (BEP20)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Rate: <b>1 USDT = ₹{rate:.2f}</b>\n\n"
        f"💰 Enter amount in <b>USDT</b>:\n\n"
        f"📉 Min: <b>{min_usdt:.2f} USDT</b>\n"
        f"📈 Max: <b>{max_usdt:.2f} USDT</b>\n\n"
        f"⚠️ <i>Send only via BEP20 (BSC) network!</i>\n\n"
        f"Send the amount you want to deposit:",
        reply_markup=get_cancel_kb(),
    )
    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USDT FLOW — STEP 2 (Validate → Show Address)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallet_request_router.message(
    WalletRequestStates.entering_amount,
)
async def msg_enter_usdt_amount(
    message: Message,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """Validate USDT amount → show address + rate."""

    from bot.services.rate_service import (
        get_usdt_inr_rate,
    )

    if not message.text:
        await message.answer(
            "❌ Please send a number.",
            reply_markup=get_cancel_kb(),
        )
        return

    text_input = message.text.strip()
    if text_input.lower() in ("/cancel", "cancel"):
        await state.clear()
        await message.answer(
            "❌ Deposit cancelled.",
            reply_markup=get_back_menu_kb(lang),
        )
        return

    try:
        amount = Decimal(
            text_input.replace(",", "")
        )
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer(
            "❌ Invalid amount.\n"
            "Example: <code>10</code>",
            reply_markup=get_cancel_kb(),
        )
        return

    async with get_session() as session:
        settings = SettingsRepository(session)
        min_dep = Decimal(
            str(await settings.get_float(
                SettingsRepository.KEY_MIN_DEPOSIT,
                default=10.0,
            ))
        )
        max_dep = Decimal(
            str(await settings.get_float(
                SettingsRepository.KEY_MAX_DEPOSIT,
                default=100000.0,
            ))
        )
        usdt_address = await settings.get(
            "usdt_bep20_address"
        ) or ""

    if not usdt_address:
        await message.answer(
            "⚠️ USDT deposit is unavailable. Try UPI."
        )
        return

    # Get live rate
    rate = await get_usdt_inr_rate()
    rate_decimal = Decimal(str(rate))

    inr_value = amount * rate_decimal
    min_usdt = min_dep / rate_decimal
    max_usdt = max_dep / rate_decimal

    if amount < min_usdt or amount > max_usdt:
        await message.answer(
            f"❌ Amount must be between "
            f"<b>{min_usdt:.2f} USDT</b> and "
            f"<b>{max_usdt:.2f} USDT</b>.\n\n"
            f"<i>Rate: 1 USDT = ₹{rate:.2f}</i>",
            reply_markup=get_cancel_kb(),
        )
        return

    await state.update_data(
        amount_usdt=str(amount),
        usdt_rate=str(rate),
    )

    text = (
        f"🪙 <b>USDT Deposit</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📤 Send: <b>{amount} USDT</b>\n"
        f"💰 Credit: <b>₹{inr_value:.2f}</b>\n"
        f"📊 Rate: 1 USDT = ₹{rate:.2f}\n\n"
        f"🏦 <b>Network:</b> BEP20 (BSC)\n"
        f"📋 <b>Address:</b>\n"
        f"<code>{usdt_address}</code>\n\n"
        f"⚠️ Send <b>exact</b> amount only!\n"
        f"⚠️ Use <b>BEP20</b> network only!\n\n"
        f"After sending, upload the screenshot."
    )

    await state.set_state(
        WalletRequestStates.uploading_screenshot
    )
    await message.answer(
        text,
        reply_markup=get_cancel_kb(),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USDT FLOW — STEP 3 (Screenshot Upload)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallet_request_router.message(
    WalletRequestStates.uploading_screenshot,
    F.photo,
)
async def msg_upload_usdt_screenshot(
    message: Message,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """Save screenshot + submit USDT request."""

    photo = message.photo[-1]
    file_id = photo.file_id

    await state.update_data(
        screenshot_file_id=file_id
    )

    await _submit_usdt_request(message, state, lang)


@wallet_request_router.message(
    WalletRequestStates.uploading_screenshot,
    ~F.photo,
)
async def msg_usdt_screenshot_not_photo(
    message: Message,
    **kwargs,
) -> None:
    """Handle non-photo uploads."""
    await message.answer(
        "❌ Please send a <b>screenshot</b> "
        "of your payment.",
        reply_markup=get_cancel_kb(),
    )


async def _submit_usdt_request(
    message: Message,
    state: FSMContext,
    lang: str,
) -> None:
    """Save USDT request to DB + notify owners."""

    data = await state.get_data()
    await state.clear()

    user = message.from_user
    amount_usdt = Decimal(
        data.get("amount_usdt", "0")
    )
    usdt_rate = Decimal(
        data.get("usdt_rate", "1")
    )
    screenshot_file_id = data.get("screenshot_file_id")

    inr_amount = amount_usdt * usdt_rate

    async with get_session() as session:
        user_repo = UserRepository(session)
        db_user = await user_repo.get_by_telegram_id(
            user.id
        )

        if not db_user:
            await message.answer(
                "❌ User not found. Send /start first."
            )
            return

        req_repo = WalletRequestRepository(session)

        req = await req_repo.create(
            user_id=db_user.id,
            amount_inr=inr_amount,
            payment_method=PaymentMethod.USDT_BEP20,
            amount_usdt=amount_usdt,
            usdt_rate=usdt_rate,
            screenshot_file_id=screenshot_file_id,
            utr_id=None,
        )
        await session.commit()
        request_id = req.id

    await message.answer(
        f"✅ <b>Deposit Request Submitted!</b>\n\n"
        f"💰 Amount: <b>{amount_usdt} USDT</b>\n"
        f"💵 Value: <b>₹{inr_amount:.2f}</b>\n"
        f"📋 Method: <b>USDT BEP20</b>\n"
        f"🔢 Request ID: <code>#{request_id}</code>\n\n"
        f"⏳ Your request is under review.\n"
        f"You'll be notified once approved.",
        reply_markup=get_back_menu_kb(lang),
    )

    await _notify_owner_new_usdt(
        request_id=request_id,
        user=user,
        amount_usdt=amount_usdt,
        inr_amount=inr_amount,
        screenshot_file_id=screenshot_file_id,
    )


async def _notify_owner_new_usdt(
    request_id: int,
    user,
    amount_usdt: Decimal,
    inr_amount: Decimal,
    screenshot_file_id,
) -> None:
    """Send USDT deposit notification to owners."""

    from bot.keyboards.owner.wallets import (
        get_request_action_kb,
    )

    name = escape_html(
        user.first_name
        or user.username
        or str(user.id)
    )
    username = (
        f"@{user.username}"
        if user.username
        else "No username"
    )

    text = (
        f"🪙 <b>NEW USDT DEPOSIT REQUEST</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>{name}</b> ({username})\n"
        f"🆔 TG ID: <code>{user.id}</code>\n"
        f"🔢 Request: <code>#{request_id}</code>\n\n"
        f"💰 Amount: <b>{amount_usdt} USDT</b>\n"
        f"💵 Value: <b>₹{inr_amount:.2f}</b>\n"
        f"📋 Method: <b>USDT BEP20</b>\n\n"
        f"⚠️ <i>Manual verification required.</i>"
    )

    kb = get_request_action_kb(request_id)

    try:
        if screenshot_file_id:
            await notification_service.notify_owners_photo(
                photo=screenshot_file_id,
                caption=text,
                reply_markup=kb,
                setting_key=(
                    SettingsRepository
                    .KEY_BALANCE_REQ_NOTIF
                ),
            )
        else:
            await notification_service.notify_owners(
                text=text,
                reply_markup=kb,
                setting_key=(
                    SettingsRepository
                    .KEY_BALANCE_REQ_NOTIF
                ),
            )
    except Exception as e:
        log.error(f"❌ Owner notify failed: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UPI — VERIFY PAYMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallet_request_router.callback_query(
    F.data.startswith("wallet:fam_check:")
)
async def cb_fam_check_status(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """Manually verify FamGateway payment + credit."""

    order_id = callback.data.split(":")[-1]

    svc = FamGatewayService()
    status = await svc.check_status(order_id)

    if status["is_paid"]:
        approved = await auto_approve_fam_request(
            order_id=order_id,
            utr=status["utr"] or "",
            sender_name=status["sender_name"],
        )

        credited_amount = (
            float(approved.amount_inr)
            if approved else 0.0
        )

        final_caption = (
            f"✅ <b>Payment Done!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Amount: <b>₹{credited_amount:.2f}</b>\n"
            f"🔢 Order: <code>{order_id}</code>\n"
            f"🧾 UTR: <code>{status['utr'] or 'N/A'}</code>\n\n"
            f"✅ <b>Balance credited to your wallet.</b>"
        )

        await _finalize_message(callback, final_caption)

        await callback.answer(
            f"✅ Payment credited! "
            f"₹{credited_amount:.2f} added.",
            show_alert=False,
        )

    elif status["is_expired"]:
        final_caption = (
            f"⏰ <b>Order Expired</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🔢 Order: <code>{order_id}</code>\n\n"
            f"Please create a new deposit request."
        )

        await _finalize_message(callback, final_caption)

        await callback.answer(
            "⏰ Order expired.",
            show_alert=False,
        )

    else:
        await callback.answer(
            "⏳ Payment not received yet.\n"
            "Complete the UPI transfer and wait 5 seconds.",
            show_alert=True,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OWNER NOTIFICATION — UPI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _notify_owner_new_order(
    request_id: int,
    user,
    amount_inr: Decimal,
    fam_order_id: str,
) -> None:
    """Notify owners of new UPI order."""

    name = escape_html(
        user.first_name
        or user.username
        or str(user.id)
    )
    username = (
        f"@{user.username}"
        if user.username
        else "No username"
    )

    text = (
        f"💳 <b>NEW UPI ORDER CREATED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>{name}</b> ({username})\n"
        f"🆔 TG ID: <code>{user.id}</code>\n"
        f"🔢 DB ID: <code>#{request_id}</code>\n"
        f"🔗 Order: <code>{fam_order_id}</code>\n\n"
        f"💰 Amount: <b>₹{format_money(amount_inr)}</b>\n"
        f"📋 Method: <b>UPI (FamGateway)</b>\n\n"
        f"⏳ <i>Auto-verification pending...</i>"
    )

    try:
        await notification_service.notify_owners(
            text=text,
            setting_key=(
                SettingsRepository
                .KEY_BALANCE_REQ_NOTIF
            ),
        )
    except Exception as e:
        log.error(f"❌ Owner notify failed: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CANCEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@wallet_request_router.callback_query(
    F.data == "wallet:cancel_request"
)
async def cb_cancel_deposit(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """Cancel deposit flow."""

    await state.clear()

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None,
        )
    except Exception:
        pass

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.answer(
        "❌ Cancelled", show_alert=False
    )

    await callback.message.answer(
        "❌ Deposit request cancelled.",
        reply_markup=get_back_menu_kb(lang),
    )
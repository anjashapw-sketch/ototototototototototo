"""
Add single account handler.
Phone → OTP → 2FA → Success flow.
Tracks added accounts for stock notify.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    OwnerRepository,
    SettingsRepository,
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.owner.confirmations import (
    get_add_account_cancel_kb,
    get_add_another_kb,
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU,
)
from bot.services.account_manager import (
    AccountManager,
)
from bot.services.country_detector import (
    country_detector,
)
from bot.services.session_manager import (
    session_manager,
)
from bot.states.add_account import (
    AddAccountStates,
)
from bot.utils.flag_emoji import get_flag
from bot.utils.helpers import (
    generate_random_password,
)
from bot.utils.logger import log
from bot.utils.phone_utils import normalize_phone
from bot.utils.validators import validate_otp


add_account_router = Router(name="own_add_acc")
add_account_router.message.filter(IsOwner())
add_account_router.callback_query.filter(IsOwner())


# ━━━ ENTRY POINTS ━━━

@add_account_router.message(
    F.text == OWNER_MENU["add_account"]
)
async def msg_add_account_init(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Start add account flow (reply kb)."""
    await _start_flow(message, state)


@add_account_router.callback_query(
    F.data == "own:add_acc"
)
async def cb_add_account_init(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Start add account flow (callback).
    Preserves added_accounts list.
    """
    try:
        await callback.message.delete()
    except Exception:
        pass

    await _start_flow(callback.message, state)
    await callback.answer()


async def _start_flow(
    message: Message,
    state: FSMContext,
) -> None:
    """Prompt for phone number.
    Keep added_accounts list intact.
    """
    # Preserve added_accounts list
    data = await state.get_data()
    added_list = data.get("added_accounts", [])

    await state.clear()
    await state.update_data(
        added_accounts=added_list
    )

    text = (
        "➕ <b>ADD NEW ACCOUNT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📞 Enter phone number with\n"
        "country code:\n\n"
        "Example: <code>+919876543210</code>"
    )

    if added_list:
        text += (
            f"\n\n📦 Added this session: "
            f"<b>{len(added_list)}</b>"
        )

    await message.answer(
        text,
        reply_markup=get_add_account_cancel_kb(),
    )
    await state.set_state(
        AddAccountStates.waiting_phone
    )


# ━━━ CANCEL HANDLER ━━━

@add_account_router.callback_query(
    F.data == "own:add_acc_cancel"
)
async def cb_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Cancel add account flow."""
    data = await state.get_data()
    client = data.get("client")
    added_list = data.get("added_accounts", [])

    if client:
        try:
            await client.disconnect()
        except Exception:
            pass

    await state.clear()
    # Preserve added list for notify
    if added_list:
        await state.update_data(
            added_accounts=added_list
        )

    try:
        if added_list:
            await callback.message.edit_text(
                f"❌ Cancelled.\n\n"
                f"📦 Added this session: "
                f"<b>{len(added_list)}</b>",
                reply_markup=get_add_another_kb(
                    added_count=len(added_list)
                ),
            )
        else:
            await callback.message.edit_text(
                "❌ Cancelled."
            )
    except Exception:
        pass

    await callback.answer()


# ━━━ STATE: WAITING PHONE ━━━

@add_account_router.message(
    AddAccountStates.waiting_phone,
    F.text,
)
async def msg_phone(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Process phone number input."""
    phone = normalize_phone(message.text)

    if not phone:
        await message.answer(
            "❌ Invalid phone number.\n"
            "Use format: +919876543210"
        )
        return

    # Check existing accounts
    async with get_session() as session:
        repo = AccountRepository(session)

        active = await repo.get_active_by_phone(
            phone
        )
        if active:
            await message.answer(
                "❌ This phone is already in stock\n"
                "with active session.\n"
                "Cannot add the same number twice."
            )
            await state.set_state(None)
            return

        old = await repo.get_by_phone(phone)
        if old:
            await repo.delete_old_record(phone)
            await message.answer(
                "ℹ️ Old record found and cleared.\n"
                "Re-adding fresh session..."
            )

    # Detect country
    code, name = country_detector.detect(phone)
    flag = get_flag(code)

    status_msg = await message.answer(
        f"⏳ Sending OTP to {phone}...\n"
        f"<i>Using stealth mode...</i>"
    )

    result = await session_manager.send_code(
        phone
    )

    if not result.success:
        await status_msg.edit_text(
            f"❌ Failed to send OTP:\n"
            f"{result.message}"
        )
        return

    await state.update_data(
        phone=phone,
        country_code=code,
        country_name=name,
        client=result.data["client"],
        phone_code_hash=(
            result.data["phone_code_hash"]
        ),
        fingerprint=result.data["fingerprint"],
    )

    await status_msg.edit_text(
        f"📨 <b>OTP SENT</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📞 Phone: <code>{phone}</code>\n"
        f"🌍 Detected: {flag} {name}\n\n"
        f"OTP has been sent.\n"
        f"Enter the OTP code:",
        reply_markup=get_add_account_cancel_kb(),
    )

    await state.set_state(
        AddAccountStates.waiting_otp
    )


# ━━━ STATE: WAITING OTP ━━━

@add_account_router.message(
    AddAccountStates.waiting_otp,
    F.text,
)
async def msg_otp(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Process OTP input."""
    otp = validate_otp(message.text)

    if not otp:
        await message.answer(
            "❌ Invalid OTP format.\n"
            "Enter the 5-6 digit code."
        )
        return

    data = await state.get_data()
    client = data["client"]
    phone = data["phone"]
    phone_code_hash = data["phone_code_hash"]

    status_msg = await message.answer(
        "⏳ Verifying OTP...\n"
        "<i>Mimicking human delay...</i>"
    )

    result = await session_manager.verify_code(
        client=client,
        phone=phone,
        phone_code_hash=phone_code_hash,
        code=otp,
    )

    # Case 1: Success without 2FA
    if result.success:
        session_string = (
            result.data["session_string"]
        )

        auto_2fa_pass = await _set_auto_2fa(
            session_string, data["fingerprint"]
        )

        await _save_account(
            message=message,
            state=state,
            status_msg=status_msg,
            session_string=session_string,
            twofa_password=auto_2fa_pass,
            auto_2fa=True,
        )
        return

    # Case 2: Needs 2FA
    if result.data.get("needs_2fa"):
        await state.update_data(
            client=result.data["client"]
        )
        await status_msg.edit_text(
            "🔐 <b>2FA REQUIRED</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "This account has 2FA enabled.\n"
            "Enter the 2FA password:",
            reply_markup=(
                get_add_account_cancel_kb()
            ),
        )
        await state.set_state(
            AddAccountStates.waiting_2fa
        )
        return

    # Case 3: Failed
    await status_msg.edit_text(
        f"❌ {result.message}\n\n"
        "Try again or cancel.",
        reply_markup=get_add_account_cancel_kb(),
    )


# ━━━ STATE: WAITING 2FA ━━━

@add_account_router.message(
    AddAccountStates.waiting_2fa,
    F.text,
)
async def msg_2fa(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Process 2FA password."""
    password = message.text.strip()

    if not password:
        await message.answer(
            "❌ Empty password not allowed."
        )
        return

    data = await state.get_data()
    client = data["client"]

    status_msg = await message.answer(
        "⏳ Verifying 2FA..."
    )

    result = await session_manager.verify_2fa(
        client=client,
        password=password,
    )

    if not result.success:
        await status_msg.edit_text(
            f"❌ {result.message}\n\n"
            "Try again or cancel.",
            reply_markup=(
                get_add_account_cancel_kb()
            ),
        )
        return

    session_string = (
        result.data["session_string"]
    )
    await _save_account(
        message=message,
        state=state,
        status_msg=status_msg,
        session_string=session_string,
        twofa_password=password,
        auto_2fa=False,
    )


# ━━━ HELPERS ━━━

async def _set_auto_2fa(
    session_string: str,
    fingerprint,
) -> str:
    """Auto-set 2FA on account."""
    auto_pass = generate_random_password(
        length=8,
        prefix=settings.default_2fa_prefix,
    )

    client = session_manager._create_client(
        session_string=session_string,
        fingerprint=fingerprint,
    )

    try:
        await client.connect()
        await client.enable_cloud_password(
            password=auto_pass,
            hint="Account Security",
        )
        log.info("✅ Auto-2FA set")
    except Exception as e:
        log.warning(f"Auto-2FA failed: {e}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    return auto_pass


async def _save_account(
    message: Message,
    state: FSMContext,
    status_msg: Message,
    session_string: str,
    twofa_password: str,
    auto_2fa: bool,
) -> None:
    """Save account to DB + track for notify."""
    data = await state.get_data()
    phone = data["phone"]
    code = data["country_code"]
    name = data["country_name"]
    flag = get_flag(code)

    user = message.from_user

    async with get_session() as session:
        owner_repo = OwnerRepository(session)
        owner = await owner_repo.get_by_telegram_id(
            user.id
        )

        manager = AccountManager(session)
        success, msg, account = (
            await manager.add_account(
                phone=phone,
                session_string=session_string,
                twofa_password=twofa_password,
                added_by=owner.id,
            )
        )

    # Preserve & update added_accounts list
    added_list = data.get("added_accounts", [])

    if success and account:
        added_list.append({
            "phone": phone,
            "country_code": code,
            "country_name": name,
            "flag": flag,
            "account_id": account.id,
        })

    # Clear current flow state
    await state.clear()

    # Restore added list
    await state.update_data(
        added_accounts=added_list
    )

    if not success:
        await status_msg.edit_text(
            f"❌ Save failed:\n{msg}"
        )
        return

    auto_note = ""
    if auto_2fa:
        auto_note = (
            f"\n\n🛡️ 2FA was not set.\n"
            f"Bot auto-set: "
            f"<code>{twofa_password}</code>"
        )

    success_text = (
        f"✅ <b>ACCOUNT ADDED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📞 Phone: <code>{phone}</code>\n"
        f"🌍 Country: {flag} {name}\n"
        f"🔐 2FA: ✅ Set\n"
        f"📊 Session: ✅ Active\n"
        f"🛡️ Stealth: ✅ Enabled\n"
        f"🆔 Stock ID: <code>"
        f"#ACC-{account.id:04d}</code>"
        f"{auto_note}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 Added this session: "
        f"<b>{len(added_list)}</b>"
    )

    await status_msg.edit_text(
        success_text,
        reply_markup=get_add_another_kb(
            added_count=len(added_list)
        ),
    )
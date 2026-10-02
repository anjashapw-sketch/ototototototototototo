"""
Bulk upload handler.
Interactive bulk account add via phone list.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.models import BatchStatus
from bot.database.models.bulk_batch import (
    BulkBatch
)
from bot.database.repositories import (
    AccountRepository,
    OwnerRepository
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.owner.bulk import (
    get_bulk_done_kb,
    get_bulk_progress_kb,
    get_bulk_start_kb,
    get_bulk_stop_confirm_kb
)
from bot.keyboards.owner.confirmations import (
    get_add_account_cancel_kb
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU
)
from bot.services.account_manager import (
    AccountManager
)
from bot.services.bulk_processor import (
    bulk_processor
)
from bot.services.country_detector import (
    country_detector
)
from bot.services.session_manager import (
    session_manager
)
from bot.states.bulk_upload import (
    BulkUploadStates
)
from bot.utils.flag_emoji import get_flag
from bot.utils.helpers import (
    generate_random_password
)
from bot.utils.logger import log
from bot.utils.phone_utils import (
    normalize_phone
)
from bot.utils.progress_bar import (
    generate_progress_bar
)
from bot.utils.validators import validate_otp
from bot.config import settings


bulk_upload_router = Router(name="own_bulk")
bulk_upload_router.message.filter(IsOwner())
bulk_upload_router.callback_query.filter(
    IsOwner()
)


# ━━━ ENTRY: ASK FOR NUMBERS ━━━

@bulk_upload_router.message(
    F.text == OWNER_MENU["bulk_upload"]
)
async def msg_bulk_init(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Start bulk upload flow."""
    # Check if another bulk is running
    running = (
        bulk_processor.get_running_owner()
    )
    if running and running != message.from_user.id:
        await message.answer(
            f"⚠️ Bulk upload already in "
            f"progress by another owner.\n"
            f"Please wait."
        )
        return

    text = (
        "📦 <b>BULK UPLOAD</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Send phone numbers (one per line):\n\n"
        "Example:\n"
        "<code>+919876543210\n"
        "+919876543211\n"
        "+15551234567</code>\n\n"
        "Min 1, Max 100 numbers."
    )

    await message.answer(
        text,
        reply_markup=get_add_account_cancel_kb()
    )

    await state.set_state(
        BulkUploadStates.waiting_numbers
    )


# ━━━ STATE: WAITING NUMBERS LIST ━━━

@bulk_upload_router.message(
    BulkUploadStates.waiting_numbers,
    F.text
)
async def msg_numbers(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Parse phone numbers list."""
    lines = message.text.strip().split("\n")
    phones = []
    invalid_count = 0

    for line in lines:
        normalized = normalize_phone(line)
        if normalized:
            phones.append(normalized)
        else:
            invalid_count += 1

    if not phones:
        await message.answer(
            "❌ No valid phone numbers found."
        )
        return

    # Remove duplicates preserving order
    phones = list(dict.fromkeys(phones))

    if len(phones) > 100:
        await message.answer(
            "❌ Max 100 numbers allowed.\n"
            f"You provided {len(phones)}."
        )
        return

    # Create batch in DB
    user = message.from_user
    async with get_session() as session:
        owner_repo = OwnerRepository(session)
        owner = await owner_repo.get_by_telegram_id(
            user.id
        )

        batch = BulkBatch(
            owner_id=owner.id,
            total_numbers=len(phones)
        )
        session.add(batch)
        await session.flush()
        batch_id = batch.id

    # Create in-memory session
    bulk_session = (
        await bulk_processor.create_session(
            owner_id=user.id,
            batch_id=batch_id,
            phones=phones
        )
    )

    info_text = (
        f"📦 <b>BULK UPLOAD READY</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Total Numbers: {len(phones)}\n"
        f"✅ Completed: 0\n"
        f"⏳ Pending: {len(phones)}\n\n"
        f"Progress:\n"
        f"{generate_progress_bar(0, len(phones))}\n\n"
        f"Ready to start processing?"
    )

    sent = await message.answer(
        info_text,
        reply_markup=get_bulk_start_kb()
    )

    bulk_session.progress_message_id = (
        sent.message_id
    )

    # Don't set processing state yet; wait
    # for user to press "Start Processing"


# ━━━ START / CANCEL CONTROLS ━━━

@bulk_upload_router.callback_query(
    F.data == "own:bulk_start"
)
async def cb_bulk_start(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Start processing the batch."""
    owner_id = callback.from_user.id
    bs = bulk_processor.get_session(owner_id)

    if not bs:
        await callback.answer(
            "❌ No active batch",
            show_alert=True
        )
        return

    if bs.started:
        await callback.answer(
            "⚠️ Already started"
        )
        return

    bs.started = True
    await callback.answer("▶️ Starting...")

    # Process first number
    await _process_next(
        callback.message, state, bs
    )


@bulk_upload_router.callback_query(
    F.data == "own:bulk_cancel"
)
async def cb_bulk_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Cancel before starting."""
    owner_id = callback.from_user.id
    await bulk_processor.remove_session(
        owner_id
    )
    await _cleanup_batch(
        owner_id, BatchStatus.CANCELLED
    )
    await state.clear()

    try:
        await callback.message.edit_text(
            "❌ Bulk upload cancelled."
        )
    except Exception:
        pass

    await callback.answer()


@bulk_upload_router.callback_query(
    F.data == "own:bulk_stop"
)
async def cb_bulk_stop_init(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Confirm stop bulk."""
    owner_id = callback.from_user.id
    bs = bulk_processor.get_session(owner_id)

    if not bs:
        await callback.answer(
            "❌ No active batch",
            show_alert=True
        )
        return

    text = (
        f"⏹ <b>STOP BULK UPLOAD?</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Progress: {bs.successful + bs.failed + bs.skipped}"
        f"/{bs.total}\n"
        f"Remaining: {bs.pending}"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_bulk_stop_confirm_kb()
        )
    except Exception:
        pass

    await callback.answer()


@bulk_upload_router.callback_query(
    F.data == "own:bulk_stop_yes"
)
async def cb_bulk_stop_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Actually stop the bulk."""
    owner_id = callback.from_user.id
    bs = bulk_processor.get_session(owner_id)

    if bs:
        bs.stopped = True

    await _finish_bulk(
        callback.message, state, owner_id
    )
    await callback.answer("⏹ Stopped")


@bulk_upload_router.callback_query(
    F.data == "own:bulk_continue"
)
async def cb_bulk_continue(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Continue from stop confirmation."""
    owner_id = callback.from_user.id
    bs = bulk_processor.get_session(owner_id)

    if not bs:
        await callback.answer()
        return

    await _show_otp_prompt(
        callback.message, bs, edit=True
    )
    await callback.answer()


@bulk_upload_router.callback_query(
    F.data == "own:bulk_skip"
)
async def cb_bulk_skip(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Skip current number."""
    owner_id = callback.from_user.id
    bs = bulk_processor.get_session(owner_id)

    if not bs or not bs.current_phone:
        await callback.answer()
        return

    bs.skipped += 1
    bs.failed_log.append({
        "phone": bs.current_phone,
        "reason": "Skipped by owner"
    })

    # Cleanup current client
    if bs.current_client:
        try:
            await bs.current_client.disconnect()
        except Exception:
            pass
        bs.current_client = None

    await callback.answer("⏭ Skipped")
    await _process_next(
        callback.message, state, bs
    )


# ━━━ OTP / 2FA INPUT HANDLERS ━━━

@bulk_upload_router.message(
    BulkUploadStates.waiting_otp,
    F.text
)
async def msg_bulk_otp(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Process OTP for current number."""
    owner_id = message.from_user.id
    bs = bulk_processor.get_session(owner_id)

    if not bs or not bs.current_client:
        await message.answer(
            "❌ No active number. Bulk reset."
        )
        await state.clear()
        return

    otp = validate_otp(message.text)
    if not otp:
        await message.answer(
            "❌ Invalid OTP format."
        )
        return

    result = await session_manager.verify_code(
        client=bs.current_client,
        phone=bs.current_phone,
        phone_code_hash=bs.current_hash,
        code=otp
    )

    # Success no 2FA
    if result.success:
        session_string = (
            result.data["session_string"]
        )
        auto_2fa = await _set_auto_2fa_for_bulk(
            session_string,
            bs.current_fingerprint
        )
        await _save_bulk_account(
            session_string=session_string,
            twofa_password=auto_2fa,
            bs=bs,
            owner_tg_id=owner_id
        )
        bs.current_client = None
        await _process_next(
            message, state, bs
        )
        return

    # Needs 2FA
    if result.data.get("needs_2fa"):
        bs.current_client = result.data["client"]
        await message.answer(
            "🔐 2FA required.\n"
            "Enter the 2FA password:"
        )
        await state.set_state(
            BulkUploadStates.waiting_2fa
        )
        return

    # Failed
    bs.failed += 1
    bs.failed_log.append({
        "phone": bs.current_phone,
        "reason": result.message
    })
    bs.current_client = None
    await message.answer(
        f"❌ Failed: {result.message}\n"
        f"Moving to next..."
    )
    await _process_next(
        message, state, bs
    )


@bulk_upload_router.message(
    BulkUploadStates.waiting_2fa,
    F.text
)
async def msg_bulk_2fa(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Process 2FA for current number."""
    owner_id = message.from_user.id
    bs = bulk_processor.get_session(owner_id)

    if not bs or not bs.current_client:
        await state.clear()
        return

    password = message.text.strip()
    if not password:
        await message.answer(
            "❌ Empty password."
        )
        return

    result = await session_manager.verify_2fa(
        client=bs.current_client,
        password=password
    )

    if not result.success:
        bs.failed += 1
        bs.failed_log.append({
            "phone": bs.current_phone,
            "reason": result.message
        })
        bs.current_client = None
        await message.answer(
            f"❌ 2FA failed: {result.message}\n"
            f"Moving to next..."
        )
        await _process_next(
            message, state, bs
        )
        return

    session_string = (
        result.data["session_string"]
    )
    await _save_bulk_account(
        session_string=session_string,
        twofa_password=password,
        bs=bs,
        owner_tg_id=owner_id
    )
    bs.current_client = None
    await _process_next(message, state, bs)


# ━━━ CORE PROCESS NEXT ━━━

async def _process_next(
    message: Message,
    state: FSMContext,
    bs
) -> None:
    """Move to the next number."""
    if bs.stopped:
        await _finish_bulk(
            message, state, bs.owner_id
        )
        return

    if bs.current_index >= len(bs.phones):
        await _finish_bulk(
            message, state, bs.owner_id
        )
        return

    phone = bs.phones[bs.current_index]
    bs.current_index += 1
    bs.current_phone = phone

    # Check for duplicates
    async with get_session() as session:
        repo = AccountRepository(session)
        if await repo.get_by_phone(phone):
            bs.skipped += 1
            bs.failed_log.append({
                "phone": phone,
                "reason": "Duplicate in DB"
            })
            await _process_next(
                message, state, bs
            )
            return

    # Send OTP
    result = await session_manager.send_code(
        phone
    )

    if not result.success:
        bs.failed += 1
        bs.failed_log.append({
            "phone": phone,
            "reason": result.message
        })
        await _process_next(
            message, state, bs
        )
        return

    bs.current_client = result.data["client"]
    bs.current_hash = (
        result.data["phone_code_hash"]
    )
    bs.current_fingerprint = (
        result.data["fingerprint"]
    )

    await _show_otp_prompt(message, bs)
    await state.set_state(
        BulkUploadStates.waiting_otp
    )


async def _show_otp_prompt(
    message: Message,
    bs,
    edit: bool = False
) -> None:
    """Show the OTP prompt with progress."""
    code, name = country_detector.detect(
        bs.current_phone
    )
    flag = get_flag(code)

    done = bs.successful + bs.failed + bs.skipped

    text = (
        f"📨 <b>OTP REQUIRED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 Current: <code>"
        f"{bs.current_phone}</code>\n"
        f"🌍 {flag} {name}\n\n"
        f"📊 Progress: {bs.current_index}"
        f"/{bs.total}\n"
        f"{generate_progress_bar(done, bs.total)}\n\n"
        f"✅ Done: {bs.successful}\n"
        f"❌ Failed: {bs.failed}\n"
        f"⏭ Skipped: {bs.skipped}\n"
        f"⏳ Pending: {bs.pending}\n\n"
        f"📩 Enter OTP for this number:"
    )

    try:
        if edit:
            await message.edit_text(
                text,
                reply_markup=(
                    get_bulk_progress_kb()
                )
            )
        else:
            sent = await message.answer(
                text,
                reply_markup=(
                    get_bulk_progress_kb()
                )
            )
            bs.progress_message_id = (
                sent.message_id
            )
    except Exception as e:
        log.warning(
            f"Progress msg error: {e}"
        )


# ━━━ HELPERS ━━━

async def _set_auto_2fa_for_bulk(
    session_string: str,
    fingerprint
) -> str:
    """Auto-set 2FA on bulk account."""
    auto_pass = generate_random_password(
        length=8,
        prefix=settings.default_2fa_prefix
    )

    client = session_manager._create_client(
        session_string=session_string,
        fingerprint=fingerprint
    )

    try:
        await client.connect()
        await client.enable_cloud_password(
            password=auto_pass,
            hint="Ghost Market"
        )
    except Exception as e:
        log.warning(
            f"Bulk auto-2FA error: {e}"
        )
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    return auto_pass


async def _save_bulk_account(
    session_string: str,
    twofa_password: str,
    bs,
    owner_tg_id: int
) -> None:
    """Save successful bulk account."""
    async with get_session() as session:
        owner_repo = OwnerRepository(session)
        owner = await owner_repo.get_by_telegram_id(
            owner_tg_id
        )

        manager = AccountManager(session)
        success, msg, _ = (
            await manager.add_account(
                phone=bs.current_phone,
                session_string=session_string,
                twofa_password=twofa_password,
                added_by=owner.id
            )
        )

    if success:
        bs.successful += 1
        log.info(
            f"✅ Bulk added: {bs.current_phone}"
        )
    else:
        bs.failed += 1
        bs.failed_log.append({
            "phone": bs.current_phone,
            "reason": msg
        })


async def _finish_bulk(
    message: Message,
    state: FSMContext,
    owner_id: int
) -> None:
    """Send final bulk report."""
    bs = bulk_processor.get_session(owner_id)
    if not bs:
        return

    await _cleanup_batch(
        owner_id, BatchStatus.DONE, bs
    )
    await state.clear()

    text = (
        f"🎉 <b>BULK UPLOAD COMPLETE</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Total: {bs.total}\n"
        f"{generate_progress_bar(bs.total, bs.total)}\n\n"
        f"✅ Successful: {bs.successful}\n"
        f"❌ Failed: {bs.failed}\n"
        f"⏭ Skipped: {bs.skipped}\n"
    )

    if bs.failed_log:
        text += "\n━━ FAILED/SKIPPED ━━\n"
        for entry in bs.failed_log[:10]:
            phone = entry["phone"]
            reason = entry["reason"][:50]
            text += f"\n❌ {phone}\n   {reason}"
        if len(bs.failed_log) > 10:
            text += (
                f"\n\n...and "
                f"{len(bs.failed_log) - 10} more"
            )

    try:
        await message.answer(
            text,
            reply_markup=get_bulk_done_kb()
        )
    except Exception:
        pass

    await bulk_processor.remove_session(
        owner_id
    )


async def _cleanup_batch(
    owner_id: int,
    status: BatchStatus,
    bs=None
) -> None:
    """Update batch status in DB."""
    if not bs:
        bs = bulk_processor.get_session(owner_id)
    if not bs:
        return

    from datetime import datetime
    from sqlalchemy import update

    async with get_session() as session:
        await session.execute(
            update(BulkBatch)
            .where(BulkBatch.id == bs.batch_id)
            .values(
                successful=bs.successful,
                failed=bs.failed,
                skipped=bs.skipped,
                status=status,
                completed_at=datetime.utcnow()
            )
        )
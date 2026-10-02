"""
Admin management handler.
Add/remove admins (superadmin only).
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.models.owner import OwnerRole
from bot.database.repositories import (
    OwnerRepository
)
from bot.filters.is_owner import IsOwner
from bot.filters.is_superadmin import (
    IsSuperadmin
)
from bot.keyboards.owner.admins import (
    get_admins_overview_kb,
    get_remove_admin_list_kb
)
from bot.keyboards.owner.confirmations import (
    get_owner_back_kb
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU
)
from bot.states.admin_add import AdminAddStates
from bot.utils.helpers import escape_html
from bot.utils.logger import log
from bot.utils.validators import (
    validate_telegram_id
)


admins_router = Router(name="own_admins")
admins_router.message.filter(IsOwner())
admins_router.callback_query.filter(IsOwner())


# ━━━ OVERVIEW ━━━

@admins_router.message(
    F.text == OWNER_MENU["admins"]
)
async def msg_admins(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Show admins overview."""
    await state.clear()
    await _show_overview(
        message, message.from_user.id
    )


@admins_router.callback_query(
    F.data == "own:admins"
)
async def cb_admins(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Admins callback."""
    await state.clear()
    await _show_overview(
        callback.message,
        callback.from_user.id,
        edit=True
    )
    await callback.answer()


async def _show_overview(
    message: Message,
    user_tg_id: int,
    edit: bool = False
) -> None:
    """Build admins overview."""
    async with get_session() as session:
        repo = OwnerRepository(session)
        is_super = await repo.is_superadmin(
            user_tg_id
        )
        owners = await repo.get_all()

    superadmins = [
        o for o in owners
        if o.role == OwnerRole.SUPERADMIN
    ]
    admins = [
        o for o in owners
        if o.role == OwnerRole.ADMIN
    ]

    text = (
        "👑 <b>ADMIN MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 Superadmins: <code>"
        f"{len(superadmins)}</code>\n"
        f"🛡️ Admins: <code>{len(admins)}</code>\n\n"
        f"━━ CURRENT ADMINS ━━\n"
    )

    for owner in owners:
        icon = (
            "👑" if owner.role ==
            OwnerRole.SUPERADMIN else "🛡️"
        )
        name = (
            f"@{escape_html(owner.username)}"
            if owner.username
            else str(owner.telegram_id)
        )
        text += (
            f"\n{icon} {name} "
            f"({owner.role.value})"
        )

    kb = get_admins_overview_kb(
        is_superadmin=is_super
    )

    if edit:
        try:
            await message.edit_text(
                text, reply_markup=kb
            )
        except Exception:
            pass
    else:
        await message.answer(
            text, reply_markup=kb
        )


# ━━━ ADD ADMIN (Superadmin only) ━━━

@admins_router.callback_query(
    F.data == "own:admin_add",
    IsSuperadmin()
)
async def cb_add_admin_init(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Start add admin flow."""
    text = (
        "➕ <b>ADD ADMIN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Send the Telegram User ID of\n"
        "the new admin:"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_owner_back_kb(
                "own:admins"
            )
        )
    except Exception:
        pass

    await state.set_state(
        AdminAddStates.waiting_user_id
    )
    await callback.answer()


@admins_router.message(
    AdminAddStates.waiting_user_id,
    F.text,
    IsSuperadmin()
)
async def msg_add_admin(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Process new admin ID."""
    tg_id = validate_telegram_id(message.text)

    if not tg_id:
        await message.answer(
            "❌ Invalid ID."
        )
        return

    async with get_session() as session:
        repo = OwnerRepository(session)

        existing = await repo.get_by_telegram_id(
            tg_id
        )
        if existing:
            await message.answer(
                "⚠️ Already an admin.",
                reply_markup=get_owner_back_kb(
                    "own:admins"
                )
            )
            await state.clear()
            return

        await repo.create(
            telegram_id=tg_id,
            role=OwnerRole.ADMIN
        )

    await state.clear()

    await message.answer(
        f"✅ Admin added.\n"
        f"ID: <code>{tg_id}</code>",
        reply_markup=get_owner_back_kb(
            "own:admins"
        )
    )

    log.info(
        f"➕ Admin added: {tg_id} by "
        f"{message.from_user.id}"
    )


# ━━━ REMOVE ADMIN (Superadmin only) ━━━

@admins_router.callback_query(
    F.data == "own:admin_rm_list",
    IsSuperadmin()
)
async def cb_remove_admin_list(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Show list of admins to remove."""
    async with get_session() as session:
        repo = OwnerRepository(session)
        admins = await repo.get_all_admins()

    if not admins:
        await callback.answer(
            "No admins to remove",
            show_alert=True
        )
        return

    text = (
        "❌ <b>REMOVE ADMIN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Select admin to remove:"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_remove_admin_list_kb(
                admins
            )
        )
    except Exception:
        pass

    await callback.answer()


@admins_router.callback_query(
    F.data.startswith("own:admin_rm:"),
    IsSuperadmin()
)
async def cb_remove_admin(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Remove admin by Telegram ID."""
    tg_id = int(callback.data.split(":")[-1])

    async with get_session() as session:
        repo = OwnerRepository(session)
        owner = await repo.get_by_telegram_id(
            tg_id
        )

        if not owner:
            await callback.answer(
                "❌ Not found",
                show_alert=True
            )
            return

        if owner.role == OwnerRole.SUPERADMIN:
            await callback.answer(
                "❌ Cannot remove superadmin",
                show_alert=True
            )
            return

        success = await repo.delete(tg_id)

    if success:
        await callback.answer(
            "✅ Admin removed",
            show_alert=True
        )
        log.info(
            f"❌ Removed admin: {tg_id} by "
            f"{callback.from_user.id}"
        )

        # Refresh
        await cb_admins(callback, state)
    else:
        await callback.answer(
            "❌ Failed",
            show_alert=True
        )
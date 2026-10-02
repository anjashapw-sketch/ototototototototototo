"""
Force subscription handler (owner side).
Add/remove channels, toggle enable.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.models.force_sub_channel \
    import ChannelType
from bot.database.repositories import (
    ForceSubRepository,
    OwnerRepository,
    SettingsRepository
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.owner.confirmations import (
    get_owner_back_kb
)
from bot.keyboards.owner.force_sub import (
    get_fsub_cancel_kb,
    get_fsub_channel_kb,
    get_fsub_list_kb,
    get_fsub_main_kb,
    get_fsub_remove_confirm_kb,
    get_fsub_type_kb
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU
)
from bot.services.force_sub_service import (
    force_sub_service
)
from bot.states.force_sub import ForceSubStates
from bot.utils.logger import log
from bot.utils.validators import (
    validate_chat_id,
    validate_invite_link,
    validate_username
)


force_sub_owner_router = Router(name="own_fsub")
force_sub_owner_router.message.filter(IsOwner())
force_sub_owner_router.callback_query.filter(
    IsOwner()
)


# ━━━ MAIN ━━━

@force_sub_owner_router.message(
    F.text == OWNER_MENU["force_sub"]
)
async def msg_fsub(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Show force sub main."""
    await state.clear()
    await _show_main(message)


@force_sub_owner_router.callback_query(
    F.data == "own:fsub"
)
async def cb_fsub(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Force sub main (callback)."""
    await state.clear()
    await _show_main(
        callback.message, edit=True
    )
    await callback.answer()


async def _show_main(
    message: Message,
    edit: bool = False
) -> None:
    """Build force sub main panel."""
    async with get_session() as session:
        fsub_repo = ForceSubRepository(session)
        channels = await fsub_repo.get_all()

        settings_repo = SettingsRepository(
            session
        )
        is_enabled = await settings_repo.get_bool(
            settings_repo.KEY_FORCE_SUB,
            default=False
        )

    public_count = sum(
        1 for c in channels
        if c.type == ChannelType.PUBLIC
    )
    private_count = sum(
        1 for c in channels
        if c.type == ChannelType.PRIVATE
    )

    status = (
        "🟢 ENABLED" if is_enabled
        else "🔴 DISABLED"
    )

    text = (
        "🔐 <b>FORCE SUBSCRIPTION</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Status: {status}\n\n"
        f"📊 Total Channels: <code>"
        f"{len(channels)}</code>\n"
        f"┣➔ 🌐 Public: <code>"
        f"{public_count}</code>\n"
        f"┗➔ 🔒 Private: <code>"
        f"{private_count}</code>"
    )

    kb = get_fsub_main_kb(is_enabled)

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


# ━━━ TOGGLE ━━━

@force_sub_owner_router.callback_query(
    F.data == "own:fsub_toggle"
)
async def cb_toggle(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Toggle force sub on/off."""
    async with get_session() as session:
        repo = SettingsRepository(session)
        new_val = await repo.toggle_bool(
            repo.KEY_FORCE_SUB
        )

    status = "ENABLED" if new_val else "DISABLED"
    await callback.answer(
        f"✅ Force Sub: {status}",
        show_alert=True
    )

    log.info(
        f"🔐 Force sub={new_val} by "
        f"{callback.from_user.id}"
    )

    await _show_main(
        callback.message, edit=True
    )


# ━━━ ADD CHANNEL FLOW ━━━

@force_sub_owner_router.callback_query(
    F.data == "own:fsub_add"
)
async def cb_add_init(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Show type selection."""
    text = (
        "➕ <b>ADD CHANNEL/GROUP</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Select entity type:\n\n"
        "🌐 <b>PUBLIC</b>\n"
        "┗➔ Has @username\n\n"
        "🔒 <b>PRIVATE</b>\n"
        "┗➔ No username, only invite link"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_fsub_type_kb()
        )
    except Exception:
        pass

    await callback.answer()


@force_sub_owner_router.callback_query(
    F.data == "own:fsub_type:public"
)
async def cb_type_public(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Start public channel add."""
    text = (
        "🌐 <b>ADD PUBLIC CHANNEL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Send channel username or link:\n\n"
        "Examples:\n"
        "┣➔ <code>@GhostUpdates</code>\n"
        "┣➔ <code>GhostUpdates</code>\n"
        "┗➔ <code>t.me/GhostUpdates</code>\n\n"
        "⚠️ Bot must be ADMIN in channel."
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_fsub_cancel_kb()
        )
    except Exception:
        pass

    await state.set_state(
        ForceSubStates.waiting_public_username
    )
    await callback.answer()


@force_sub_owner_router.message(
    ForceSubStates.waiting_public_username,
    F.text
)
async def msg_public_username(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Process public username."""
    username = validate_username(message.text)

    if not username:
        await message.answer(
            "❌ Invalid username."
        )
        return

    status_msg = await message.answer(
        "⏳ Verifying..."
    )

    # Resolve to chat ID
    chat_id, title = (
        await force_sub_service
        .resolve_public_username(username)
    )

    if not chat_id:
        await status_msg.edit_text(
            "❌ Channel not found or "
            "bot not added.",
            reply_markup=get_fsub_cancel_kb()
        )
        return

    # Verify bot admin
    is_admin, msg, info = (
        await force_sub_service.verify_channel(
            chat_id
        )
    )

    if not is_admin:
        await status_msg.edit_text(
            f"❌ {msg}",
            reply_markup=get_fsub_cancel_kb()
        )
        return

    # Save to DB
    user = message.from_user
    async with get_session() as session:
        owner_repo = OwnerRepository(session)
        owner = await owner_repo.get_by_telegram_id(
            user.id
        )

        fsub_repo = ForceSubRepository(session)

        # Check duplicate
        existing = await fsub_repo.get_by_chat_id(
            chat_id
        )
        if existing:
            await status_msg.edit_text(
                "⚠️ This channel is already added.",
                reply_markup=get_owner_back_kb(
                    "own:fsub"
                )
            )
            await state.clear()
            return

        await fsub_repo.create(
            name=title or username,
            type=ChannelType.PUBLIC,
            chat_id=chat_id,
            invite_link=(
                f"https://t.me/{username}"
            ),
            username=username,
            is_bot_admin=True,
            added_by=owner.id
        )

    await state.clear()

    text = (
        f"✅ <b>CHANNEL ADDED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 Name: {title or username}\n"
        f"🆔 ID: <code>{chat_id}</code>\n"
        f"🔗 Link: t.me/{username}\n"
        f"🌐 Type: Public\n"
        f"✅ Bot Status: Admin"
    )

    await status_msg.edit_text(
        text,
        reply_markup=get_owner_back_kb(
            "own:fsub"
        )
    )

    log.info(
        f"🔐 Public channel added: "
        f"{username} ({chat_id})"
    )


@force_sub_owner_router.callback_query(
    F.data == "own:fsub_type:private"
)
async def cb_type_private(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Start private channel add."""
    text = (
        "🔒 <b>ADD PRIVATE CHANNEL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Step 1 of 2\n\n"
        "Send the INVITE LINK:\n\n"
        "Example:\n"
        "<code>https://t.me/+abc123xyz</code>\n\n"
        "ℹ️ This link will be shown to users."
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_fsub_cancel_kb()
        )
    except Exception:
        pass

    await state.set_state(
        ForceSubStates.waiting_private_link
    )
    await callback.answer()


@force_sub_owner_router.message(
    ForceSubStates.waiting_private_link,
    F.text
)
async def msg_private_link(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Process private invite link."""
    link = validate_invite_link(message.text)

    if not link:
        await message.answer(
            "❌ Invalid invite link.\n"
            "Must start with t.me/+ or "
            "t.me/joinchat/"
        )
        return

    await state.update_data(invite_link=link)

    text = (
        f"🔒 <b>ADD PRIVATE CHANNEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Step 2 of 2\n\n"
        f"✅ Link saved:\n"
        f"<code>{link}</code>\n\n"
        f"Now send the NUMERIC ID:\n\n"
        f"Example: <code>-1001234567890</code>\n\n"
        f"❓ How to get ID?\n"
        f"┣➔ Forward msg from channel to\n"
        f"┃   @userinfobot\n"
        f"┗➔ Or use @ShowJsonBot\n\n"
        f"⚠️ Bot must be ADMIN in channel."
    )

    await message.answer(
        text,
        reply_markup=get_fsub_cancel_kb()
    )

    await state.set_state(
        ForceSubStates.waiting_private_chat_id
    )


@force_sub_owner_router.message(
    ForceSubStates.waiting_private_chat_id,
    F.text
)
async def msg_private_chat_id(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Process numeric chat ID."""
    chat_id = validate_chat_id(message.text)

    if not chat_id:
        await message.answer(
            "❌ Invalid chat ID.\n"
            "Must be negative (-100...)."
        )
        return

    status_msg = await message.answer(
        "⏳ Verifying..."
    )

    # Verify bot admin
    is_admin, msg, info = (
        await force_sub_service.verify_channel(
            chat_id
        )
    )

    if not is_admin:
        await status_msg.edit_text(
            f"❌ {msg}",
            reply_markup=get_fsub_cancel_kb()
        )
        return

    data = await state.get_data()
    invite_link = data["invite_link"]

    user = message.from_user
    async with get_session() as session:
        owner_repo = OwnerRepository(session)
        owner = await owner_repo.get_by_telegram_id(
            user.id
        )

        fsub_repo = ForceSubRepository(session)

        existing = await fsub_repo.get_by_chat_id(
            chat_id
        )
        if existing:
            await status_msg.edit_text(
                "⚠️ This channel is already added.",
                reply_markup=get_owner_back_kb(
                    "own:fsub"
                )
            )
            await state.clear()
            return

        await fsub_repo.create(
            name=info.get("title", "Private"),
            type=ChannelType.PRIVATE,
            chat_id=chat_id,
            invite_link=invite_link,
            is_bot_admin=True,
            added_by=owner.id
        )

    await state.clear()

    text = (
        f"✅ <b>CHANNEL ADDED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 Name: {info.get('title')}\n"
        f"🆔 ID: <code>{chat_id}</code>\n"
        f"🔗 Link: {invite_link}\n"
        f"🔒 Type: Private\n"
        f"✅ Bot Status: Admin"
    )

    await status_msg.edit_text(
        text,
        reply_markup=get_owner_back_kb(
            "own:fsub"
        )
    )

    log.info(
        f"🔐 Private channel added: "
        f"{chat_id}"
    )


# ━━━ LIST CHANNELS ━━━

@force_sub_owner_router.callback_query(
    F.data == "own:fsub_list"
)
async def cb_list(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Show all channels."""
    async with get_session() as session:
        repo = ForceSubRepository(session)
        channels = await repo.get_all()

    if not channels:
        await callback.answer(
            "No channels added",
            show_alert=True
        )
        return

    text = (
        f"📋 <b>MANAGE CHANNELS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Total: <code>{len(channels)}</code>"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_fsub_list_kb(
                channels
            )
        )
    except Exception:
        pass

    await callback.answer()


@force_sub_owner_router.callback_query(
    F.data.startswith("own:fsub_view:")
)
async def cb_view(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """View single channel."""
    channel_id = int(
        callback.data.split(":")[-1]
    )

    async with get_session() as session:
        repo = ForceSubRepository(session)
        channel = await repo.get_by_id(
            channel_id
        )

    if not channel:
        await callback.answer(
            "❌ Not found",
            show_alert=True
        )
        return

    icon = (
        "🔒" if channel.type ==
        ChannelType.PRIVATE else "🌐"
    )
    bot_status = (
        "✅ Yes" if channel.is_bot_admin
        else "❌ No"
    )

    text = (
        f"{icon} <b>CHANNEL DETAILS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 Name: {channel.name}\n"
        f"🆔 ID: <code>{channel.chat_id}</code>\n"
        f"🔗 Link: {channel.invite_link}\n"
        f"📊 Type: {channel.type.value}\n"
        f"✅ Bot Admin: {bot_status}"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_fsub_channel_kb(
                channel_id
            )
        )
    except Exception:
        pass

    await callback.answer()


# ━━━ RECHECK BOT ADMIN ━━━

@force_sub_owner_router.callback_query(
    F.data.startswith("own:fsub_recheck:")
)
async def cb_recheck(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Recheck bot admin status."""
    channel_id = int(
        callback.data.split(":")[-1]
    )

    await callback.answer(
        "⏳ Checking...",
        show_alert=False
    )

    async with get_session() as session:
        repo = ForceSubRepository(session)
        channel = await repo.get_by_id(
            channel_id
        )

        if not channel:
            await callback.answer(
                "❌ Not found",
                show_alert=True
            )
            return

        is_admin, msg, _ = (
            await force_sub_service
            .verify_channel(channel.chat_id)
        )

        await repo.update_bot_admin_status(
            channel_id, is_admin
        )

    emoji = "✅" if is_admin else "❌"
    await callback.answer(
        f"{emoji} {msg}",
        show_alert=True
    )

    await cb_view(callback)


# ━━━ REMOVE CHANNEL ━━━

@force_sub_owner_router.callback_query(
    F.data.startswith("own:fsub_remove:")
)
async def cb_remove_init(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Confirm channel removal."""
    channel_id = int(
        callback.data.split(":")[-1]
    )

    text = (
        "⚠️ <b>REMOVE CHANNEL?</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "This channel will be removed\n"
        "from force subscription list.\n\n"
        "Bot will NOT leave the channel."
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=(
                get_fsub_remove_confirm_kb(
                    channel_id
                )
            )
        )
    except Exception:
        pass

    await callback.answer()


@force_sub_owner_router.callback_query(
    F.data.startswith("own:fsub_rm_yes:")
)
async def cb_remove_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Actually remove channel."""
    channel_id = int(
        callback.data.split(":")[-1]
    )

    async with get_session() as session:
        repo = ForceSubRepository(session)
        success = await repo.delete(channel_id)

    if success:
        await callback.answer(
            "✅ Removed",
            show_alert=True
        )
        log.info(
            f"🔐 Channel removed: {channel_id}"
        )
        await cb_list(callback)
    else:
        await callback.answer(
            "❌ Failed",
            show_alert=True
        )


# ━━━ EDIT INVITE LINK ━━━

@force_sub_owner_router.callback_query(
    F.data.startswith("own:fsub_editlink:")
)
async def cb_edit_link_init(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Ask for new invite link."""
    channel_id = int(
        callback.data.split(":")[-1]
    )

    await state.update_data(
        edit_channel_id=channel_id
    )

    text = (
        "✏️ <b>EDIT INVITE LINK</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Send the new invite link:"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_owner_back_kb(
                f"own:fsub_view:{channel_id}"
            )
        )
    except Exception:
        pass

    await state.set_state(
        ForceSubStates.waiting_edit_link
    )
    await callback.answer()


@force_sub_owner_router.message(
    ForceSubStates.waiting_edit_link,
    F.text
)
async def msg_edit_link(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Save new invite link."""
    link = validate_invite_link(message.text)

    if not link:
        # For public channels, accept plain
        # username/URL
        from bot.utils.validators import (
            validate_username
        )
        username = validate_username(
            message.text
        )
        if username:
            link = (
                f"https://t.me/{username}"
            )

    if not link:
        await message.answer(
            "❌ Invalid link or username."
        )
        return

    data = await state.get_data()
    channel_id = data.get("edit_channel_id")

    if not channel_id:
        await state.clear()
        return

    async with get_session() as session:
        repo = ForceSubRepository(session)
        await repo.update_invite_link(
            channel_id, link
        )

    await state.clear()

    await message.answer(
        f"✅ Link updated.",
        reply_markup=get_owner_back_kb(
            f"own:fsub_view:{channel_id}"
        )
    )

    log.info(
        f"🔐 Link updated: ch={channel_id}"
    )
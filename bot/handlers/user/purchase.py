"""
Purchase handler.
Handles the buy flow with confirmation.
Shows 2FA password immediately after purchase.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    PricingRepository,
    UserRepository,
)
from bot.keyboards.user.account import (
    get_account_details_kb,
)
from bot.keyboards.user.common import (
    get_back_menu_kb,
)
from bot.keyboards.user.purchase import (
    get_accept_view_kb,
    get_purchase_confirm_kb,
)
from bot.locales.i18n import i18n
from bot.services.account_manager import (
    AccountManager,
)
from bot.services.notification import (
    notification_service,
)
from bot.utils.flag_emoji import get_flag
from bot.utils.formatters import (
    format_date,
    format_money,
    format_phone_pretty,
)
from bot.utils.helpers import escape_html
from bot.utils.logger import log


purchase_router = Router(name="purchase")


@purchase_router.callback_query(
    F.data.startswith("shop:buy:")
)
async def cb_buy_init(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs,
) -> None:
    """Show purchase confirmation."""
    country_code = callback.data.split(":")[-1]
    user = callback.from_user

    async with get_session() as session:
        user_repo = UserRepository(session)
        db_user = (
            await user_repo.get_by_telegram_id(
                user.id
            )
        )

        # Check stock
        acc_repo = AccountRepository(session)
        countries = (
            await acc_repo.get_stock_by_country()
        )
        country_data = next(
            (
                (code, name, count)
                for code, name, count in countries
                if code == country_code
            ),
            None,
        )

        if not country_data:
            await callback.answer(
                i18n.get(
                    "error_out_of_stock", lang
                ),
                show_alert=True,
            )
            return

        code, name, _ = country_data

        # Get price
        pricing_repo = PricingRepository(session)
        price = await pricing_repo.get_price(code)

    # Check balance
    if db_user.wallet_balance < price:
        short = price - db_user.wallet_balance
        text = i18n.get(
            "error_insufficient_balance",
            lang=lang,
            balance=format_money(
                db_user.wallet_balance
            ),
            required=format_money(price),
            short=format_money(short),
        )
        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_back_menu_kb(
                    lang
                ),
            )
        except Exception:
            pass
        await callback.answer()
        return

    # Show confirm screen
    flag = get_flag(code)
    after = db_user.wallet_balance - price

    text = i18n.get(
        "purchase_confirm",
        lang=lang,
        flag=flag,
        country=name,
        price=format_money(price),
        balance=format_money(
            db_user.wallet_balance
        ),
        after=format_money(after),
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=(
                get_purchase_confirm_kb(
                    code, lang
                )
            ),
        )
    except Exception:
        pass

    await callback.answer()


@purchase_router.callback_query(
    F.data.startswith("buy:confirm:")
)
async def cb_buy_confirm(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs,
) -> None:
    """Execute purchase and show 2FA immediately."""
    country_code = callback.data.split(":")[-1]
    user = callback.from_user

    async with get_session() as session:
        user_repo = UserRepository(session)
        db_user = (
            await user_repo.get_by_telegram_id(
                user.id
            )
        )

        manager = AccountManager(session)
        success, msg, account = (
            await manager.purchase_account(
                user_id=db_user.id,
                country_code=country_code,
            )
        )

        if success:
            # Get updated balance
            new_balance = (
                await manager.wallet.get_balance(
                    db_user.id
                )
            )

            # Decrypt 2FA password
            twofa_password = manager.decrypt_2fa(
                account
            )

    if not success:
        # Failed
        if "Insufficient" in msg:
            error_text = i18n.get(
                "error_insufficient_balance",
                lang=lang,
                balance=format_money(
                    db_user.wallet_balance
                ),
                required="?",
                short="?",
            )
        elif "stock" in msg.lower():
            error_text = i18n.get(
                "error_out_of_stock", lang
            )
        else:
            error_text = i18n.get(
                "error_generic", lang
            )

        try:
            await callback.message.edit_text(
                error_text,
                reply_markup=get_back_menu_kb(
                    lang
                ),
            )
        except Exception:
            pass

        await callback.answer(
            "❌ Failed", show_alert=True
        )
        return

    # ━━━ SUCCESS — Show everything ━━━
    flag = get_flag(account.country_code)
    pretty_phone = format_phone_pretty(
        account.phone
    )
    twofa_display = (
        twofa_password
        if twofa_password
        else "❌ Not set"
    )

    text = (
        f"✅ <b>PURCHASE SUCCESSFUL!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 <b>Phone:</b>\n"
        f"<code>{pretty_phone}</code>\n\n"
        f"🔐 <b>2FA Password:</b>\n"
        f"<code>{twofa_display}</code>\n\n"
        f"🌍 <b>Country:</b> {flag} "
        f"{escape_html(account.country_name)}\n"
        f"🆔 <b>Account ID:</b> "
        f"<code>#ACC-{account.id:04d}</code>\n"
        f"💰 <b>New Balance:</b> "
        f"<code>${format_money(new_balance)}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>What's next?</b>\n"
        f"1️⃣ Get OTP from button below\n"
        f"2️⃣ Login on your Telegram\n"
        f"3️⃣ Remove our session anytime\n\n"
        f"⚠️ <i>Save these details safely!\n"
        f"You can view them anytime in\n"
        f"\"My Accounts\".</i>"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_account_details_kb(
                account.id, lang
            ),
        )
    except Exception:
        # Fallback — send new message
        await callback.message.answer(
            text,
            reply_markup=get_account_details_kb(
                account.id, lang
            ),
        )

    await callback.answer(
        "✅ Purchased!", show_alert=False
    )

    # Notify owners
    await _notify_sale(
        account, db_user, new_balance
    )

    log.info(
        f"✅ Purchase: user={db_user.id}, "
        f"acc={account.id}"
    )


@purchase_router.callback_query(
    F.data == "buy:cancel"
)
async def cb_buy_cancel(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs,
) -> None:
    """Cancel purchase, back to shop."""
    from bot.handlers.user.shop import (
        cb_shop_list,
    )
    await cb_shop_list(callback, lang)


@purchase_router.callback_query(
    F.data.startswith("acc:view:")
)
async def cb_view_account(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs,
) -> None:
    """Show full account details after accept."""
    acc_id = int(callback.data.split(":")[-1])
    user = callback.from_user

    async with get_session() as session:
        user_repo = UserRepository(session)
        db_user = (
            await user_repo.get_by_telegram_id(
                user.id
            )
        )

        acc_repo = AccountRepository(session)
        account = await acc_repo.get_by_id(acc_id)

        if (
            not account
            or account.sold_to != db_user.id
        ):
            await callback.answer(
                "❌ Account not found",
                show_alert=True,
            )
            return

        manager = AccountManager(session)
        twofa = manager.decrypt_2fa(account)

    flag = get_flag(account.country_code)
    pretty_phone = format_phone_pretty(
        account.phone
    )
    status_text = (
        "✅ Active"
        if account.session_alive
        else "❌ Removed"
    )
    twofa_display = (
        twofa if twofa else "❌ Not set"
    )
    sold_date = format_date(account.sold_date)

    text = (
        f"📱 <b>ACCOUNT DETAILS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📞 <b>Phone:</b>\n"
        f"<code>{pretty_phone}</code>\n\n"
        f"🔐 <b>2FA Password:</b>\n"
        f"<code>{twofa_display}</code>\n\n"
        f"🌍 <b>Country:</b> {flag} "
        f"{escape_html(account.country_name)}\n"
        f"📅 <b>Purchased:</b> {sold_date}\n"
        f"📊 <b>Status:</b> {status_text}\n"
        f"🆔 <b>ID:</b> "
        f"<code>#ACC-{account.id:04d}</code>"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_account_details_kb(
                acc_id, lang
            ),
        )
    except Exception:
        pass

    await callback.answer()


async def _notify_sale(
    account, user, new_balance
) -> None:
    """Notify owners of sale."""
    from bot.database.repositories import (
        SettingsRepository,
    )

    flag = get_flag(account.country_code)
    name = (
        user.first_name
        or user.username
        or str(user.telegram_id)
    )

    text = (
        f"💰 <b>NEW SALE</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 Phone: <code>{account.phone}</code>\n"
        f"🌍 Country: {flag} "
        f"{account.country_name}\n"
        f"💵 Price: "
        f"${format_money(account.price)}\n"
        f"👤 Buyer: {name}\n"
        f"🆔 User ID: "
        f"<code>{user.telegram_id}</code>"
    )

    await notification_service.notify_owners(
        text=text,
        setting_key=(
            SettingsRepository.KEY_SALE_NOTIF
        ),
    )
"""
Shop handler.
Browse accounts by country.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    PricingRepository
)
from bot.keyboards.user.shop import (
    get_countries_kb,
    get_country_details_kb
)
from bot.locales.i18n import i18n
from bot.utils.flag_emoji import get_flag
from bot.utils.formatters import format_money


shop_router = Router(name="shop")


async def show_shop(
    message: Message,
    lang: str = "en"
) -> None:
    """
    Display shop with country list.
    Called from reply keyboard or directly.
    """
    async with get_session() as session:
        repo = AccountRepository(session)
        countries = (
            await repo.get_stock_by_country()
        )

    if not countries:
        await message.answer(
            i18n.get("shop_empty", lang)
        )
        return

    await message.answer(
        i18n.get("shop_title", lang),
        reply_markup=get_countries_kb(
            countries, lang
        )
    )


@shop_router.callback_query(
    F.data == "shop:list"
)
async def cb_shop_list(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs
) -> None:
    """Show country list (callback)."""
    async with get_session() as session:
        repo = AccountRepository(session)
        countries = (
            await repo.get_stock_by_country()
        )

    if not countries:
        try:
            await callback.message.edit_text(
                i18n.get("shop_empty", lang)
            )
        except Exception:
            pass
        await callback.answer()
        return

    try:
        await callback.message.edit_text(
            i18n.get("shop_title", lang),
            reply_markup=get_countries_kb(
                countries, lang
            )
        )
    except Exception:
        pass

    await callback.answer()


@shop_router.callback_query(
    F.data.startswith("shop:country:")
)
async def cb_country_details(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs
) -> None:
    """Show details for selected country."""
    country_code = callback.data.split(":")[-1]

    async with get_session() as session:
        acc_repo = AccountRepository(session)
        countries = (
            await acc_repo.get_stock_by_country()
        )

        # Find this country's stock
        country_data = next(
            (
                (code, name, count)
                for code, name, count in countries
                if code == country_code
            ),
            None
        )

        if not country_data:
            await callback.answer(
                i18n.get(
                    "error_out_of_stock", lang
                ),
                show_alert=True
            )
            return

        code, name, stock = country_data

        pricing_repo = PricingRepository(session)
        price = await pricing_repo.get_price(
            code
        )

    flag = get_flag(code)
    text = i18n.get(
        "country_details",
        lang=lang,
        flag=flag,
        country=name,
        stock=stock,
        price=format_money(price)
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_country_details_kb(
                code, stock, lang
            )
        )
    except Exception:
        pass

    await callback.answer()
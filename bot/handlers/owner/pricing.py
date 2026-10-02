"""
Pricing management handler.
View, set, edit country prices.
"""

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    PricingRepository
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.owner.confirmations import (
    get_owner_back_kb
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU
)
from bot.keyboards.owner.pricing import (
    get_pricing_overview_kb
)
from bot.services.country_detector import (
    country_detector
)
from bot.states.pricing import PricingStates
from bot.utils.flag_emoji import (
    get_country_name, get_flag
)
from bot.utils.formatters import format_money
from bot.utils.logger import log
from bot.utils.validators import validate_amount


pricing_router = Router(name="own_pricing")
pricing_router.message.filter(IsOwner())
pricing_router.callback_query.filter(IsOwner())


# ━━━ OVERVIEW ━━━

@pricing_router.message(
    F.text == OWNER_MENU["pricing"]
)
async def msg_pricing(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Show pricing overview."""
    await state.clear()
    await _show_overview(message)


@pricing_router.callback_query(
    F.data == "own:pricing"
)
async def cb_pricing(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Pricing overview (callback)."""
    await state.clear()
    await _show_overview(
        callback.message, edit=True
    )
    await callback.answer()


async def _show_overview(
    message: Message,
    edit: bool = False
) -> None:
    """Build pricing overview."""
    async with get_session() as session:
        repo = PricingRepository(session)
        prices = await repo.get_all()
        default_price = await repo.get_default()

    text = (
        "💲 <b>PRICING CONTROL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🌍 Default Price: <code>"
        f"{format_money(default_price)}</code>\n\n"
        f"━━ COUNTRY PRICES ━━"
    )

    if not prices:
        text += "\n\nNo country prices set yet."

    kb = get_pricing_overview_kb(prices)

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


# ━━━ SET DEFAULT PRICE ━━━

@pricing_router.callback_query(
    F.data == "own:price_default"
)
async def cb_set_default(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Ask for default price."""
    text = (
        "💲 <b>SET DEFAULT PRICE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Enter default price (used when\n"
        "country price not set):"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_owner_back_kb(
                "own:pricing"
            )
        )
    except Exception:
        pass

    await state.set_state(
        PricingStates.waiting_default_price
    )
    await callback.answer()


@pricing_router.message(
    PricingStates.waiting_default_price,
    F.text
)
async def msg_set_default(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Save default price."""
    amount = validate_amount(message.text)

    if not amount:
        await message.answer(
            "❌ Invalid amount."
        )
        return

    async with get_session() as session:
        repo = PricingRepository(session)
        await repo.set_price(
            country_code=repo.DEFAULT_KEY,
            country_name="Default",
            price=amount
        )

    await state.clear()

    await message.answer(
        f"✅ Default price set: "
        f"{format_money(amount)}",
        reply_markup=get_owner_back_kb(
            "own:pricing"
        )
    )

    log.info(
        f"💲 Default price: {amount} by "
        f"{message.from_user.id}"
    )


# ━━━ SET COUNTRY PRICE ━━━

@pricing_router.callback_query(
    F.data == "own:price_set"
)
async def cb_set_country(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Ask for country code."""
    text = (
        "💲 <b>SET COUNTRY PRICE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Step 1 of 2\n\n"
        "Send the 2-letter country code\n"
        "(e.g., <code>IN</code>, "
        "<code>US</code>, <code>RU</code>)\n\n"
        "Or send any phone number:\n"
        "<code>+919876543210</code>"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_owner_back_kb(
                "own:pricing"
            )
        )
    except Exception:
        pass

    await state.set_state(
        PricingStates.waiting_country_code
    )
    await callback.answer()


@pricing_router.message(
    PricingStates.waiting_country_code,
    F.text
)
async def msg_country_code(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Process country code or phone."""
    text = message.text.strip()
    code = None
    name = None

    if text.startswith("+") or text.isdigit():
        # Phone number
        from bot.utils.phone_utils import (
            normalize_phone
        )
        phone = normalize_phone(text)
        if phone:
            code, name = country_detector.detect(
                phone
            )
    elif len(text) == 2 and text.isalpha():
        # Country code
        code = text.upper()
        name = get_country_name(code)

    if not code or code == "XX" or not name:
        await message.answer(
            "❌ Invalid country code or phone.\n"
            "Try again with a valid code."
        )
        return

    flag = get_flag(code)

    await state.update_data(
        country_code=code,
        country_name=name
    )

    await message.answer(
        f"✅ Country: {flag} {name}\n\n"
        f"Step 2 of 2\n\n"
        f"Now enter the price:",
        reply_markup=get_owner_back_kb(
            "own:pricing"
        )
    )

    await state.set_state(
        PricingStates.waiting_price
    )


@pricing_router.message(
    PricingStates.waiting_price,
    F.text
)
async def msg_set_country_price(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Save country price."""
    amount = validate_amount(message.text)

    if not amount:
        await message.answer(
            "❌ Invalid amount."
        )
        return

    data = await state.get_data()
    code = data["country_code"]
    name = data["country_name"]

    async with get_session() as session:
        repo = PricingRepository(session)
        await repo.set_price(
            country_code=code,
            country_name=name,
            price=amount
        )

    await state.clear()

    flag = get_flag(code)

    await message.answer(
        f"✅ Price set:\n"
        f"{flag} {name}: "
        f"{format_money(amount)}",
        reply_markup=get_owner_back_kb(
            "own:pricing"
        )
    )

    log.info(
        f"💲 Price set: {code}={amount} by "
        f"{message.from_user.id}"
    )


# ━━━ EDIT EXISTING PRICE ━━━

@pricing_router.callback_query(
    F.data.startswith("own:price_edit:")
)
async def cb_edit_existing(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Edit existing country price."""
    code = callback.data.split(":")[-1]

    async with get_session() as session:
        repo = PricingRepository(session)
        pricing = await repo.get_by_country(code)

    if not pricing:
        await callback.answer(
            "❌ Not found",
            show_alert=True
        )
        return

    await state.update_data(
        country_code=code,
        country_name=pricing.country_name
    )

    flag = (
        "🌍" if code == "DEFAULT"
        else get_flag(code)
    )

    text = (
        f"💲 <b>EDIT PRICE</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{flag} {pricing.country_name}\n"
        f"Current: <code>"
        f"{format_money(pricing.price)}</code>\n\n"
        f"Enter new price:"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_owner_back_kb(
                "own:pricing"
            )
        )
    except Exception:
        pass

    await state.set_state(
        PricingStates.waiting_price
    )
    await callback.answer()
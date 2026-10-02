"""Account details keyboards."""

from aiogram.types import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from aiogram.enums import ButtonStyle

from bot.keyboards.builder import (
    blue, build_kb, red
)
from bot.locales.i18n import i18n


def get_account_details_kb(
    acc_id: int,
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """Account details action keyboard."""
    return build_kb([
        [
            blue(
                i18n.get("btn_view_otp", lang),
                f"acc:otp:{acc_id}"
            )
        ],
        [
            red(
                i18n.get(
                    "btn_remove_device", lang
                ),
                f"acc:remove:{acc_id}"
            )
        ],
        [
            blue(
                i18n.get("btn_back", lang),
                "acc:my_list"
            )
        ]
    ])


def get_otp_kb(
    acc_id: int,
    otp_code: str = None,
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """OTP view keyboard with copy button."""
    rows = []

    # Copy OTP button if code exists
    if otp_code:
        rows.append([
            InlineKeyboardButton(
                text=i18n.get(
                    "btn_copy_otp", lang
                ),
                copy_text=CopyTextButton(
                    text=otp_code
                ),
                style=ButtonStyle.PRIMARY
            )
        ])

    rows.append([
        blue(
            i18n.get("btn_refresh", lang),
            f"acc:otp:{acc_id}"
        ),
        blue(
            i18n.get("btn_back", lang),
            f"acc:details:{acc_id}"
        )
    ])

    return build_kb(rows)


def get_remove_confirm_kb(
    acc_id: int,
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """Remove device confirmation keyboard."""
    return build_kb([
        [
            red(
                i18n.get(
                    "btn_yes_logout", lang
                ),
                f"acc:remove_yes:{acc_id}"
            ),
            blue(
                i18n.get("btn_cancel", lang),
                f"acc:details:{acc_id}"
            )
        ]
    ])


def get_my_accounts_kb(
    accounts: list,
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """List of purchased accounts."""
    from bot.utils.flag_emoji import get_flag
    from bot.utils.formatters import (
        format_phone_masked
    )

    rows = []
    for acc in accounts:
        flag = get_flag(acc.country_code)
        masked = format_phone_masked(acc.phone)

        status_text = i18n.get(
            "status_active" if acc.session_alive
            else "status_removed",
            lang
        )

        text = f"{flag} {masked} | {status_text}"
        rows.append([
            blue(text, f"acc:details:{acc.id}")
        ])

    rows.append([
        blue(
            i18n.get("btn_back_menu", lang),
            "menu:main"
        )
    ])

    return build_kb(rows)
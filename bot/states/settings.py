"""FSM states for bot settings."""

from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    """States for editing settings."""

    # Existing
    waiting_threshold = State()

    # Payment Settings
    waiting_upi_id = State()
    waiting_upi_qr = State()

    waiting_usdt_address = State()
    waiting_usdt_rate = State()

    waiting_min_deposit = State()
    waiting_max_deposit = State()

    # ── FamGateway (NEW) ──
    waiting_fam_daily_limit = State()

    # Support
    waiting_support_username = State()
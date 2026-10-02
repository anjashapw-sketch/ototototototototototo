"""FSM states for pricing operations."""

from aiogram.fsm.state import State, StatesGroup


class PricingStates(StatesGroup):
    """States for editing prices."""

    waiting_country_code = State()
    waiting_country_name = State()
    waiting_price = State()
    waiting_default_price = State()
    editing_existing = State()
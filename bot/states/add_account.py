"""FSM states for add account flow."""

from aiogram.fsm.state import State, StatesGroup


class AddAccountStates(StatesGroup):
    """States for single account add."""

    waiting_phone = State()
    waiting_otp = State()
    waiting_2fa = State()
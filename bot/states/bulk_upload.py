"""FSM states for bulk upload flow."""

from aiogram.fsm.state import State, StatesGroup


class BulkUploadStates(StatesGroup):
    """States for bulk upload flow."""

    waiting_numbers = State()
    waiting_otp = State()
    waiting_2fa = State()
    processing = State()
"""FSM states for force subscription."""

from aiogram.fsm.state import State, StatesGroup


class ForceSubStates(StatesGroup):
    """States for adding channels."""

    waiting_public_username = State()
    waiting_private_link = State()
    waiting_private_chat_id = State()
    waiting_edit_link = State()
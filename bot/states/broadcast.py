"""FSM states for broadcast messages."""

from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    """States for broadcasting."""

    waiting_message = State()
    waiting_confirm = State()
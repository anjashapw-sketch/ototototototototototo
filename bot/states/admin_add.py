"""
FSM states for admin & user management.
Holds states for admin add, user search,
user messaging, and admin balance ops.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminAddStates(StatesGroup):
    """States for adding new admin."""

    waiting_user_id = State()


class UserSearchStates(StatesGroup):
    """States for searching/messaging users."""

    waiting_user_id = State()
    waiting_message = State()


class WalletAdminStates(StatesGroup):
    """States for admin wallet operations."""

    waiting_user_id = State()
    waiting_amount = State()
"""Wallet request FSM states."""

from aiogram.fsm.state import State, StatesGroup


class WalletRequestStates(StatesGroup):
    """States for wallet top-up flow."""

    # Step 1 — choose method
    choosing_method = State()

    # Step 2 — enter amount
    entering_amount = State()

    # Step 3 — upload screenshot
    uploading_screenshot = State()

    # Step 4 — UPI only: enter UTR
    entering_utr = State()

    # Owner side — reject with note
    entering_reject_note = State()

    # ── FamGateway auto UPI (NEW) ──
    entering_fam_amount = State()
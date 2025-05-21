from aiogram.fsm.state import StatesGroup, State


class BookingStates(StatesGroup):
    """Состояния при записи пользователя"""
    choosing_category = State()
    choosing_master = State()
    choosing_service = State()
    viewing_service = State()
    choosing_date = State()
    choosing_time = State()
    asking_name = State()  # ← новое
    asking_phone = State()  # ← новое
    confirming_booking = State()

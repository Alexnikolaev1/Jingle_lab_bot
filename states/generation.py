from aiogram.fsm.state import State, StatesGroup


class GenerationStates(StatesGroup):
    """FSM: пользователь выбрал режим кнопкой и ждёт текстовый промт."""

    waiting_prompt = State()

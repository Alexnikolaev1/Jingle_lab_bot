from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """Не используется как длинный FSM — только флаг активного тура."""
    active = State()

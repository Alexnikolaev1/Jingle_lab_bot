from aiogram.fsm.state import State, StatesGroup


class WizardStates(StatesGroup):
    mood = State()
    duration = State()
    style = State()
    confirm = State()

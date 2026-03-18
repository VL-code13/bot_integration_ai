from aiogram.fsm.state import State, StatesGroup


class GptStates(StatesGroup):
    chatting = State()


class TalkStates(StatesGroup):
    choosing_person = State()
    chatting = State()


class QuizStates(StatesGroup):
    choosing_topic = State()
    answering = State()

class VocabStates(StatesGroup):
    learning = State()   # режим изучения слов
    training = State()   # режим тренировки
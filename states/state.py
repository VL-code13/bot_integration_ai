from aiogram.fsm.state import State, StatesGroup

# https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/index.html
class GptStates(StatesGroup):
    chatting = State()


class TalkStates(StatesGroup):
    '''Состояние для режима диалога с известной личностью'''
    choosing_person = State()
    chatting = State()


class QuizStates(StatesGroup):
    '''Состояние режима викторины'''
    choosing_topic = State()
    answering = State()

class VocabStates(StatesGroup):
    '''Состояние для словарного тренажера'''
    learning = State()   # режим изучения слов
    training = State()   # режим тренировки

class ResumeStates(StatesGroup):
    """
    Состояния пошагового сбора данных для составления резюме.
    """
    waiting_name = State()
    waiting_position = State()
    waiting_education = State()
    waiting_experience = State()
    waiting_skills = State()
    waiting_additional = State()
    showing_result = State()
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from prompts import TOPICS

def main_menu() -> InlineKeyboardMarkup:
    '''Клавиатура главного меню'''
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🎲 Случайный факт', callback_data='menu:random', style='primary')],
            [InlineKeyboardButton(text='🤖 Chat GPT', callback_data='menu:gpt', style='primary')],
            [InlineKeyboardButton(text='🗣️ Диалог с личностью', callback_data='menu:talk', style='primary')],
            [InlineKeyboardButton(text='🎯 Викторина', callback_data='menu:quiz', style='primary')],
            [InlineKeyboardButton(text='🆎 Словарный тренажер', callback_data='menu:vocab', style='primary')],
        ]
    )
    return keyboard


def random_keyboard() -> InlineKeyboardMarkup:
    '''Клавиатура для случайного факта'''
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🎲 Хочу еще факт', callback_data='random:again')],
            [InlineKeyboardButton(text='⛔️ Закончить', callback_data='random:stop',style='danger')],
        ]
    )


def gpt_keyboard() -> InlineKeyboardMarkup:
    '''Клавиатура диалога с Chat GPT'''
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='📛Закончить', callback_data='gpt:stop', style='danger')]
        ]
    )


def persons_keyboard(persons):
    '''Клавиатура выбора известной личности'''
    buttons = [
        [InlineKeyboardButton(text=f'{data["emoji"]} {data["name"]}', callback_data=f'talk:person:{key}')]
        for key, data in persons.items()
    ]
    buttons.append([
        InlineKeyboardButton(text='⛔️ Отмена', callback_data='talk:cancel', style='danger')
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def talk_keyboard():
    '''Клавиатура во время диалога с известной личностью'''
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🔄 Сменить собеседника', callback_data='talk:change')],
            [InlineKeyboardButton(text='⛔️ Закончить', callback_data='talk:stop', style='danger')],
        ]
    )


def topics_keyboard(topics: dict) -> InlineKeyboardMarkup:
    '''Клавиатура выбора тем викторины'''
    buttons = [
        [InlineKeyboardButton(text=topic['name'], callback_data=f'quiz:topic:{key}')]
        for key, topic in topics.items()
    ]
    buttons.append(
        [InlineKeyboardButton(text='⛔️ Отмена', callback_data='quiz:cancel', style='danger')]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quiz_actions_keyboard() -> InlineKeyboardMarkup:
    '''Клавиатура действия во время викторины'''
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='▶️ Следующий вопрос', callback_data=f'quiz:next', style='success')],
            [InlineKeyboardButton(text='🔄 Сменить тему', callback_data=f'quiz:change_topic', style='primary')],
            [InlineKeyboardButton(text='🛑 Закончить викторину', callback_data=f'quiz:stop', style='danger')],
        ]
    )


def vocab_actions_keyboard(has_words: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура действий словарного тренажёра.
    Кнопка 'Тренироваться' появляется только если есть хотя бы одно слово.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='📖 Ещё слово', callback_data='vocab:next', style='success')
    if has_words:
        builder.button(text='🎯 Тренироваться', callback_data='vocab:train', style='primary')
    builder.button(text='❌ Закончить', callback_data='vocab:stop', style='danger')
    builder.adjust(1)
    return builder.as_markup()

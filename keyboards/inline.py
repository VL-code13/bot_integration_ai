"""
Общие inline-клавиатуры бота.

Docs InlineKeyboardBuilder:
https://docs.aiogram.dev/en/latest/utils/keyboard.html#inlinekeyboardbuilder

Docs InlineKeyboardMarkup:
https://core.telegram.org/bots/api#inlinekeyboardmarkup
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    """
    Клавиатура главного меню бота.
    Каждая кнопка запускает соответствующий раздел через callback_data.

    Returns:
        InlineKeyboardMarkup с кнопками всех разделов.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='🎲 Случайный факт', callback_data='menu:random')
    builder.button(text='🤖 Chat GPT', callback_data='menu:gpt')
    builder.button(text='🗣️ Диалог с личностью', callback_data='menu:talk')
    builder.button(text='🎯 Викторина', callback_data='menu:quiz')
    builder.button(text='🆎 Словарный тренажёр', callback_data='menu:vocab')
    builder.button(text='📄 Помощь с резюме', callback_data='menu:resume')
    # Одна кнопка на строку
    builder.adjust(1)
    return builder.as_markup()


def random_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для раздела «Случайный факт».

    Returns:
        InlineKeyboardMarkup с кнопками «Ещё факт» и «Закончить».
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='🎲 Хочу ещё факт', callback_data='random:again')
    builder.button(text='⛔️ Закончить', callback_data='random:stop')
    builder.adjust(1)
    return builder.as_markup()


def gpt_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура диалога с Chat GPT.

    Returns:
        InlineKeyboardMarkup с кнопкой завершения диалога.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='📛 Закончить', callback_data='gpt:stop')
    return builder.as_markup()


def persons_keyboard(persons: dict) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора известной личности для диалога.

    Args:
        persons: словарь вида {key: {'name': str, 'emoji': str}, ...}.

    Returns:
        InlineKeyboardMarkup со списком личностей и кнопкой отмены.
    """
    builder = InlineKeyboardBuilder()
    for key, data in persons.items():
        builder.button(
            text=f'{data["emoji"]} {data["name"]}',
            callback_data=f'talk:person:{key}'
        )
    builder.button(text='⛔️ Отмена', callback_data='talk:cancel')
    # Личности — по одной на строку, отмена последней
    builder.adjust(1)
    return builder.as_markup()


def talk_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура во время диалога с известной личностью.

    Returns:
        InlineKeyboardMarkup с кнопками смены собеседника и завершения.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='🔄 Сменить собеседника', callback_data='talk:change')
    builder.button(text='⛔️ Закончить', callback_data='talk:stop')
    builder.adjust(1)
    return builder.as_markup()


def topics_keyboard(topics: dict) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора темы викторины.

    Args:
        topics: словарь вида {key: {'name': str}, ...}.

    Returns:
        InlineKeyboardMarkup со списком тем и кнопкой отмены.
    """
    builder = InlineKeyboardBuilder()
    for key, topic in topics.items():
        builder.button(
            text=topic['name'],
            callback_data=f'quiz:topic:{key}'
        )
    builder.button(text='⛔️ Отмена', callback_data='quiz:cancel')
    builder.adjust(1)
    return builder.as_markup()


def get_quiz_actions_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура действий во время викторины.

    Returns:
        InlineKeyboardMarkup с кнопками «Следующий вопрос»,
        «Сменить тему» и «Закончить».
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='▶️ Следующий вопрос', callback_data='quiz:next')
    builder.button(text='🔄 Сменить тему', callback_data='quiz:change_topic')
    builder.button(text='🛑 Закончить викторину', callback_data='quiz:stop')
    builder.adjust(1)
    return builder.as_markup()


def vocab_actions_keyboard(has_words: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура действий словарного тренажёра.
    Кнопка «Тренироваться» появляется только если есть хотя бы одно слово.

    Args:
        has_words: флаг наличия слов в словаре пользователя.

    Returns:
        InlineKeyboardMarkup с доступными действиями.

    Docs:
        https://docs.aiogram.dev/en/latest/utils/keyboard.html
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='📖 Ещё слово', callback_data='vocab:next')
    if has_words:
        builder.button(text='🎯 Тренироваться', callback_data='vocab:train')
    builder.button(text='❌ Закончить', callback_data='vocab:stop')
    builder.adjust(1)
    return builder.as_markup()

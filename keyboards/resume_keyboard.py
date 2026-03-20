"""
Клавиатуры для обработчика резюме.

Docs InlineKeyboardBuilder:
https://docs.aiogram.dev/en/latest/utils/keyboard.html#inlinekeyboardbuilder
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с единственной кнопкой отмены.
    Используется на обязательных шагах сбора данных.

    Returns:
        InlineKeyboardMarkup с кнопкой «Отмена».
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='❌ Отмена', callback_data='resume:cancel')
    return builder.as_markup()


def skip_or_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопками «Пропустить» и «Отмена».
    Используется на необязательных шагах.

    Returns:
        InlineKeyboardMarkup с двумя кнопками в одну строку.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='⏭ Пропустить', callback_data='resume:skip')
    builder.button(text='❌ Отмена', callback_data='resume:cancel')
    # adjust: https://docs.aiogram.dev/en/latest/utils/keyboard.html
    builder.adjust(2)
    return builder.as_markup()


def resume_result_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура действий после получения готового резюме.

    Кнопки:
        ✨ Улучшить      — повторная генерация с доработкой текста.
        🔄 Начать заново — очистить данные и начать с шага 1.
        🏠 В меню        — выход в главное меню.

    Returns:
        InlineKeyboardMarkup с тремя кнопками (2 + 1).
    """
    builder = InlineKeyboardBuilder()
    builder.button(text='✨ Улучшить', callback_data='resume:improve')
    builder.button(text='🔄 Начать заново', callback_data='resume:restart')
    builder.button(text='🏠 В меню', callback_data='resume:cancel')
    # Первые две рядом, третья на отдельной строке
    builder.adjust(2, 1)
    return builder.as_markup()

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура с командой /random."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="/random"))
    return builder.as_markup(resize_keyboard=True)

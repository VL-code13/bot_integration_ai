from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_fact_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline‑клавиатура для фактов с цветными кнопками (через эмодзи)."""
    builder = InlineKeyboardBuilder()

    # Зелёная кнопка — новый факт
    builder.add(InlineKeyboardButton(
        text="🟢 Ещё факт",
        callback_data="more_fact"
    ))

    # Красная кнопка — завершение
    builder.add(InlineKeyboardButton(
        text="🔴 Завершить",
        callback_data="finish"
    ))

    builder.adjust(2)  # 2 кнопки в строке
    return builder.as_markup()

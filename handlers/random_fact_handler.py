import logging
from html import escape
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.enums import ChatAction
from services.openai_service import ask_gpt
from keyboards.inline import random_keyboard, main_menu

from prompts import RANDOM_FACT

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command('random'))
async def cmd_random(message: Message):
    """Реализует старт случайного факта"""
    try:
        await send_random_fact(message)
    except Exception as e:
        logger.error(f"Ошибка в cmd_random: {e}")
        await message.answer(
            "Произошла ошибка при получении факта. Попробуйте позже.",
            reply_markup=main_menu()
        )


async def send_random_fact(message: Message):
    """Реализует отправку случайного факта"""
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING
    )

    fact = await ask_gpt(user_message=RANDOM_FACT)
    safe_fact = escape(fact)

    try:
        photo = FSInputFile('images/random.png')
        await message.answer_photo(
            photo=photo,
            caption=f'<b>Случайный факт</b>\n\n{safe_fact}',
            reply_markup=random_keyboard(),
            parse_mode='html'
        )
    except FileNotFoundError:
        logger.warning('Файл images/random.png не найден, отправляем без фото')
        await message.answer(
            f'<b>Случайный факт</b>\n\n{safe_fact}',
            reply_markup=random_keyboard(),
            parse_mode='html'
        )
    except Exception as e:
        logger.error(f'Критическая ошибка при отправке факта: {e}')
        await message.answer(
            'Произошла ошибка при получении факта.',
            reply_markup=random_keyboard()
        )


@router.callback_query(F.data == 'random:again')
async def cmd_random_again(callback: CallbackQuery):
    """Реализует еще случайный факт"""
    try:
        await callback.answer()  # Снимаем индикатор загрузки
        await send_random_fact(callback.message)
    except Exception as e:
        logger.error(f"Ошибка в cmd_random_again: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при загрузке нового факта. Используйте /random для повтора.",
            reply_markup=None
        )
        await callback.answer(
            "Ошибка загрузки факта",
            show_alert=True
        )


@router.callback_query(F.data == 'random:stop')
async def cmd_random_stop(callback: CallbackQuery):
    """Завершает режим случайного факта"""
    try:
        await callback.answer()
        await callback.message.delete()
        await callback.message.answer(
            'Выбери какой‑то пункт из меню:',
            reply_markup=main_menu()
        )
        logger.info('Завершаем режим случайного факта.')
    except Exception as e:
        logger.error(f"Ошибка в cmd_random_stop: {e}")
        # Если не удалось удалить сообщение, просто отправляем новое
        await callback.message.answer(
            'Выбери какой‑то пункт из меню:',
            reply_markup=main_menu()
        )
        await callback.answer("Ошибка при удалении сообщения", show_alert=True)

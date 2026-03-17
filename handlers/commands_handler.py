from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
import logging

from handlers.gpt_chat import cmd_gpt
from handlers.talk import cmd_talk
from keyboards.inline import main_menu
from handlers.random_fact_handler import send_random_fact
from states.state import GptStates

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command('start'))
async def cmd_start(message: Message):
    try:
        keyboard = main_menu()
        await message.answer(
            f'Привет, <b>{message.from_user.first_name or "Пользователь"}</b>\n\n'
            'Я бот с ChatGPT. Выбери что тебя интересует',
            reply_markup=keyboard,
            parse_mode='html'
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_start: {e}")
        await message.answer("Произошла ошибка. Попробуйте /start ещё раз.")

@router.message(Command('help'))
async def cmd_help(message: Message):
    try:
        await message.answer(
            '<b>Команды:</b>\n\n'
            '/start - Главное меню\n'
            '/random - Случайный факт\n'
            '/gpt - Диалог с ChatGPT\n'
            '/talk - Диалог с известной личностью\n'
            '/quiz - Викторина с подсчетом баллов\n',
            parse_mode='html'
        )
    except Exception as e:
        logger.error(f"Ошибка в cmd_help: {e}")
        await message.answer("Произошла ошибка при отображении справки.")

@router.callback_query(F.data == 'menu:random')
async def on_menu_random(callback: CallbackQuery):
    try:
        await callback.answer()
        await send_random_fact(callback.message)
    except Exception as e:
        logger.error(f"Ошибка в on_menu_random: {e}")
        await callback.answer(
            "Произошла ошибка при загрузке факта. Попробуйте позже.",
            show_alert=True
        )

@router.callback_query(F.data == 'menu:gpt')
async def on_menu_gpt(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await cmd_gpt(callback.message, state)
    except Exception as e:
        logger.error(f"Ошибка в on_menu_gpt: {e}")
        await callback.answer(
            "Произошла ошибка при запуске ChatGPT. Используйте /gpt.",
            show_alert=True
        )

@router.callback_query(F.data == 'menu:talk')
async def on_menu_talk(callback: CallbackQuery,state:FSMContext):
    try:
        await callback.answer()
        await cmd_talk(callback.message,state)
    except Exception as e:
        logger.error(f"Ошибка в on_menu_talk: {e}")
        await callback.answer("Произошла ошибка.", show_alert=True)

@router.callback_query(F.data == 'menu:quiz')
async def on_menu_quiz(callback: CallbackQuery):
    try:
        await callback.answer()
        await callback.message.answer()
    except Exception as e:
        logger.error(f"Ошибка в on_menu_quiz: {e}")
        await callback.answer("Произошла ошибка.", show_alert=True)

'''
@router.callback_query(F.data == 'menu:talk')
async def on_menu_talk(callback: CallbackQuery):
    await callback.answer() #Чтобы убрать загрузку с кнопки

@router.callback_query(F.data == 'menu:quiz')
async def on_menu_quiz(callback: CallbackQuery):
    await callback.answer() #Чтобы убрать загрузку с кнопки
'''
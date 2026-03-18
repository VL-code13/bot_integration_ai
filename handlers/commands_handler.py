import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from handlers.gpt_chat import cmd_gpt
from handlers.quiz import cmd_quiz
from handlers.talk import cmd_talk
from handlers.vocab_handler import cmd_vocab
from keyboards.inline import main_menu
from handlers.random_fact_handler import send_random_fact


logger = logging.getLogger(__name__)
router = Router()


@router.message(Command('start'))
async def cmd_start(message: Message) -> None:
    """
    Обрабатывает команду /start.
    Отправляет приветственное сообщение с главным меню.
    """
    try:
        keyboard = main_menu()
        await message.answer(
            f'Привет, <b>{message.from_user.first_name or "Пользователь"}</b>\n\n'
            'Я бот с ChatGPT. Выбери что тебя интересует',
            reply_markup=keyboard,
            parse_mode='html'
        )
    except Exception as e:
        logger.error(f'Ошибка в cmd_start: {e}')
        await message.answer('Произошла ошибка. Попробуйте /start ещё раз.')


@router.message(Command('help'))
async def cmd_help(message: Message) -> None:
    """
    Обрабатывает команду /help.
    Отправляет список доступных команд бота.
    """
    try:
        await message.answer(
            '<b>Команды:</b>\n\n'
            '/start — Главное меню\n'
            '/random — Случайный факт\n'
            '/gpt — Диалог с ChatGPT\n'
            '/talk — Диалог с известной личностью\n'
            '/quiz — Викторина с подсчётом баллов\n'
            '/vocab — Словарный тренажёр\n',
            parse_mode='html'
        )
    except Exception as e:
        logger.error(f'Ошибка в cmd_help: {e}')
        await message.answer('Произошла ошибка при отображении справки.')


@router.callback_query(F.data == 'menu:random')
async def on_menu_random(callback: CallbackQuery) -> None:
    """
    Обрабатывает нажатие кнопки 'Случайный факт' в главном меню.
    Запускает отправку случайного факта через ChatGPT.
    """
    try:
        await callback.answer()
        await send_random_fact(callback.message)
    except Exception as e:
        logger.error(f'Ошибка в on_menu_random: {e}')
        await callback.answer(
            'Произошла ошибка при загрузке факта. Попробуйте позже.',
            show_alert=True
        )


@router.callback_query(F.data == 'menu:gpt')
async def on_menu_gpt(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обрабатывает нажатие кнопки 'ChatGPT' в главном меню.
    Передаёт управление обработчику команды /gpt.
    """
    try:
        await callback.answer()
        await cmd_gpt(callback.message, state)
    except Exception as e:
        logger.error(f'Ошибка в on_menu_gpt: {e}')
        await callback.answer(
            'Произошла ошибка при запуске ChatGPT. Используйте /gpt.',
            show_alert=True
        )


@router.callback_query(F.data == 'menu:talk')
async def on_menu_talk(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обрабатывает нажатие кнопки 'Диалог с личностью' в главном меню.
    Передаёт управление обработчику команды /talk.
    """
    try:
        await callback.answer()
        await cmd_talk(callback.message, state)
    except Exception as e:
        logger.error(f'Ошибка в on_menu_talk: {e}')
        await callback.answer('Произошла ошибка.', show_alert=True)


@router.callback_query(F.data == 'menu:quiz')
async def on_menu_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обрабатывает нажатие кнопки 'Викторина' в главном меню.
    Передаёт управление обработчику команды /quiz.
    """
    try:
        await callback.answer()
        await cmd_quiz(callback.message, state)
    except Exception as e:
        logger.error(f'Ошибка в on_menu_quiz: {e}')
        await callback.answer('Произошла ошибка.', show_alert=True)


@router.callback_query(F.data == 'menu:vocab')
async def on_menu_vocab(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обрабатывает нажатие кнопки 'Словарный тренажёр' в главном меню.
    Передаёт управление обработчику команды /vocab.
    """
    try:
        await callback.answer()
        await cmd_vocab(callback.message, state)
    except Exception as e:
        logger.error(f'Ошибка в on_menu_vocab: {e}')
        await callback.answer('Произошла ошибка.', show_alert=True)

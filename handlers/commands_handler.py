from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from keyboards.inline import main_menu
from handlers.random_fact_handler import send_random_fact

router = Router()


@router.message(Command('start'))
async def cmd_start(message: Message):
    keyboard = main_menu()
    await message.answer(f'Привет, <b>{message.from_user.first_name or "Пользователь"}</b>\n\n'
                         'Я бот с ChatGPT. Выбери что тебя интересует', reply_markup=keyboard, parse_mode='html')


@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer(
        '<b>Команды:</b>\n\n'
        '/start - Главное меню\n'
        '/random - Случайный факт\n'
        '/gpt - Диалог с ChatGPT\n'
        '/talk - Диалог с известной личностью\n'
        '/help - Это сообщение',

    )

@router.callback_query(F.data == 'menu:random')
async def on_menu_random(callback: CallbackQuery):
    await callback.answer() #Чтобы убрать загрузку с кнопки
    await send_random_fact(callback.message)

@router.callback_query(F.data == 'menu:gpt')
async def on_menu_gpt(callback: CallbackQuery):
    await callback.answer() #Чтобы убрать загрузку с кнопки
    await callback.message.answer('Напиши /gpt чтобы войти в режим ChatGPT')

@router.callback_query(F.data == 'menu:talk')
async def on_menu_talk(callback: CallbackQuery):
    await callback.answer() #Чтобы убрать загрузку с кнопки

@router.callback_query(F.data == 'menu:quiz')
async def on_menu_quiz(callback: CallbackQuery):
    await callback.answer() #Чтобы убрать загрузку с кнопки
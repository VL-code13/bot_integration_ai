import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from openai import AsyncOpenAI
from config import OPENAI_API_KEY
from keyboards import get_main_keyboard, get_fact_inline_keyboard
from logger import logger
from promts import get_random_fact_prompt

router = Router()
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я бот случайных фактов. Нажмите /random для получения факта!",
        reply_markup=get_main_keyboard()
    )

@router.message(Command("random"))
async def cmd_random(message: Message):
    try:
        # Запрос к ChatGPT для получения факта
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": get_random_fact_prompt()}],
            max_tokens=100
        )
        fact_text = response.choices[0].message.content
        await message.answer(fact_text, reply_markup=get_fact_inline_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в /random: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@router.callback_query(F.data == "more_fact")
async def more_fact(callback: CallbackQuery):
    try:
        # Запрос нового факта
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": get_random_fact_prompt()}],
            max_tokens=100
        )
        fact_text = response.choices[0].message.content

        # Редактируем сообщение с новым фактом и теми же кнопками
        await callback.message.edit_text(
            text=fact_text,
            reply_markup=get_fact_inline_keyboard()
        )
        await callback.answer()  # Снимаем индикатор загрузки
    except Exception as e:
        logger.error(f"Ошибка при получении нового факта: {e}")
        await callback.answer("Произошла ошибка при получении факта.", show_alert=True)

@router.callback_query(F.data == "finish")
async def finish(callback: CallbackQuery, state: FSMContext):
    from handlers import cmd_start
    # Редактируем сообщение — убираем кнопки
    await callback.message.edit_text("Работа с ботом завершена. Используйте /random для нового факта.")
    await cmd_start(callback.message, state)
    await callback.answer()  # Снимаем индикатор загрузки

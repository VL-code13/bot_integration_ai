import logging
from html import escape
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from states.state import GptStates
from aiogram.enums import ChatAction
from services.openai_service import ask_gpt
from keyboards.inline import gpt_keyboard, main_menu
from prompts import GPT_SYSTEM_PROMT

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command('gpt'))
async def cmd_gpt(message: Message, state: FSMContext):
    try:
        await state.set_state(GptStates.chatting)
        await state.update_data(history=[])

        try:
            photo = FSInputFile('images/gpt.png')
            await message.answer_photo(
                photo=photo,
                caption=(
                    '<b>Режим ChatGPT</b>\n\n'
            'Напиши любой вопрос — я отвечу.\n'
            'Контекст диалога сохраняется.\n'
            'Нажми <b>Закончить</b>, чтобы выйти.'
                ),
                reply_markup=gpt_keyboard(),
                parse_mode='html'
            )
        except FileNotFoundError:
            logger.warning("Файл images/gpt.png не найден, отправляем текстовое сообщение")
            await message.answer(
                '<b>Режим ChatGPT</b>\n\n'
                'Напиши любой вопрос — я отвечу.\n'
                'Контекст диалога сохраняется.\n'
                'Нажми <b>Закончить</b>, чтобы выйти.',
                reply_markup=gpt_keyboard(),
                parse_mode='html'
            )
        except Exception as e:
            logger.error(f"Критическая ошибка при отправке фото в cmd_gpt: {e}")
            await message.answer(
                'Режим ChatGPT активирован. Напиши любой вопрос.',
                reply_markup=gpt_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка в cmd_gpt при установке состояния: {e}")
        await message.answer("Произошла ошибка при запуске режима ChatGPT. Попробуйте ещё раз.")

@router.message(GptStates.chatting, F.text)
async def cmd_gpt_message(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        history = data.get('history', [])

        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING
        )

        history.append({'role': 'user', 'content': message.text})

        response = await ask_gpt(
            user_message=message.text,
            system_prompt=GPT_SYSTEM_PROMT,
            history=history[:-1]
        )

        history.append({'role': 'assistant', 'content': response})

        if len(history) > 20:
            history = history[-20:]

        await state.update_data(history=history)
        await message.answer(escape(response), reply_markup=gpt_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в cmd_gpt_message: {e}")
        await message.answer(
            "Произошла ошибка при обработке запроса. Попробуйте ещё раз.",
            reply_markup=gpt_keyboard()
        )

@router.callback_query(F.data == 'gpt:stop')
async def on_gpt_stop(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.answer('Выхожу из режима ChatGPT')

        try:
            await callback.message.delete()
        except Exception as delete_error:
            logger.warning(f"Не удалось удалить сообщение: {delete_error}")

        await callback.message.answer(
            text='Выбери какой‑то пункт из меню:',
            reply_markup=main_menu()
        )
        logger.info('Режим GPT успешно завершён.')
    except Exception as e:
        logger.error(f"Критическая ошибка в on_gpt_stop: {e}")
        try:
            await callback.message.answer(
                'Выбери какой‑то пункт из меню:',
                reply_markup=main_menu()
            )
            await callback.answer("Ошибка при завершении режима GPT", show_alert=True)
        except Exception as fallback_error:
            logger.critical(f"Критическая ошибка при отправке fallback‑сообщения: {fallback_error}")
            await callback.answer(
                "Произошла критическая ошибка. Используйте /start для возврата в меню.",
                show_alert=True
            )

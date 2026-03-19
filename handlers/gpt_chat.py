import base64
import logging
from html import escape

from aiogram import Router, F
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    Message,
)

from keyboards.inline import gpt_keyboard, main_menu
from prompts import GPT_SYSTEM_PROMT
from services.openai_service import ask_gpt, ask_gpt_vision
from states.state import GptStates

router = Router()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Запуск режима GPT
# ---------------------------------------------------------------------------

@router.message(Command('gpt'))
async def cmd_gpt(message: Message, state: FSMContext) -> None:
    """
    Обрабатывает команду /gpt.
    Устанавливает состояние GptStates.chatting и отправляет
    приветственное сообщение с фото (или текстом при его отсутствии).
    """
    try:
        await state.set_state(GptStates.chatting)
        await state.update_data(history=[])

        caption = (
            '<b>Режим ChatGPT</b>\n\n'
            'Напиши любой вопрос — я отвечу.\n'
            'Можешь отправить <b>текст</b>, <b>картинку</b> или <b>стикер</b>.\n'
            'Контекст диалога сохраняется.\n'
            'Нажми <b>Закончить</b>, чтобы выйти.'
        )

        try:
            photo = FSInputFile('images/gpt.png')
            await message.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=gpt_keyboard(),
                parse_mode='html'
            )
        except FileNotFoundError:
            logger.warning('Файл images/gpt.png не найден — отправляем текст.')
            await message.answer(
                caption,
                reply_markup=gpt_keyboard(),
                parse_mode='html'
            )
    except Exception as e:
        logger.error(f'Ошибка в cmd_gpt: {e}')
        await message.answer(
            'Произошла ошибка при запуске ChatGPT. Попробуйте ещё раз.'
        )



# ---------------------------------------------------------------------------
# Обработка текста
# ---------------------------------------------------------------------------

@router.message(GptStates.chatting, F.text)
async def handle_text(message: Message, state: FSMContext) -> None:
    """
    Обрабатывает текстовое сообщение в режиме GPT.
    Передаёт текст в ChatGPT вместе с историей диалога.
    """
    try:
        data = await state.get_data()
        history: list[dict] = data.get('history', [])

        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING
        )

        response = await ask_gpt(
            user_message=message.text,
            system_prompt=GPT_SYSTEM_PROMT,
            history=history
        )

        await _update_history(state, message.text, response)
        await message.answer(escape(response), reply_markup=gpt_keyboard())

    except Exception as e:
        logger.error(f'Ошибка в handle_text: {e}')
        await message.answer(
            'Произошла ошибка при обработке запроса. Попробуйте ещё раз.',
            reply_markup=gpt_keyboard()
        )


# ---------------------------------------------------------------------------
# Обработка фото
# ---------------------------------------------------------------------------

@router.message(GptStates.chatting, F.photo)
async def handle_photo(message: Message, state: FSMContext) -> None:
    """
    Обрабатывает изображение в режиме GPT.
    Скачивает фото, кодирует в base64 и передаёт в GPT Vision.
    Подпись к фото (caption) включается в запрос, если присутствует.
    """
    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING
        )

        image_base64 = await _download_photo_as_base64(message)
        if not image_base64:
            await message.answer(
                '❌ Не удалось загрузить изображение. Попробуйте ещё раз.',
                reply_markup=gpt_keyboard()
            )
            return

        data = await state.get_data()
        history: list[dict] = data.get('history', [])

        # Если пользователь добавил подпись — используем её как вопрос,
        # иначе просим GPT описать изображение
        user_text = message.caption or 'Опиши, что изображено на картинке.'

        response = await ask_gpt_vision(
            image_base64=image_base64,
            user_text=user_text,
            system_prompt=GPT_SYSTEM_PROMT,
            history=history
        )

        await _update_history(state, f'[Изображение] {user_text}', response)
        await message.answer(escape(response), reply_markup=gpt_keyboard())

    except Exception as e:
        logger.error(f'Ошибка в handle_photo: {e}')
        await message.answer(
            'Произошла ошибка при обработке изображения. Попробуйте ещё раз.',
            reply_markup=gpt_keyboard()
        )


# ---------------------------------------------------------------------------
# Обработка стикеров
# ---------------------------------------------------------------------------

@router.message(GptStates.chatting, F.sticker)
async def handle_sticker(message: Message, state: FSMContext) -> None:
    """
    Обрабатывает стикер в режиме GPT.
    Извлекает связанный эмодзи из стикера и передаёт его в ChatGPT
    как текстовый запрос.
    """
    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING
        )

        emoji = message.sticker.emoji or '🙂'
        user_text = f'Пользователь отправил стикер с эмодзи {emoji}. Отреагируй.'

        data = await state.get_data()
        history: list[dict] = data.get('history', [])

        response = await ask_gpt(
            user_message=user_text,
            system_prompt=GPT_SYSTEM_PROMT,
            history=history
        )

        await _update_history(state, f'[Стикер {emoji}]', response)
        await message.answer(escape(response), reply_markup=gpt_keyboard())

    except Exception as e:
        logger.error(f'Ошибка в handle_sticker: {e}')
        await message.answer(
            'Произошла ошибка при обработке стикера. Попробуйте ещё раз.',
            reply_markup=gpt_keyboard()
        )


# ---------------------------------------------------------------------------
# Заглушка для неподдерживаемых типов
# ---------------------------------------------------------------------------

@router.message(GptStates.chatting)
async def handle_unsupported(message: Message, state: FSMContext) -> None:
    """
    Перехватывает любые неподдерживаемые типы сообщений в режиме GPT
    (голос, видео, документы, геолокация и т.д.).
    Уведомляет пользователя и не передаёт ничего в ChatGPT.
    """
    content_name = _get_unsupported_type_name(message)
    logger.info(
        f'Пользователь {message.from_user.id} отправил '
        f'неподдерживаемый тип: {message.content_type}'
    )
    await message.answer(
        f'⚠️ Я не умею обрабатывать {content_name}.\n\n'
        'Отправь мне <b>текст</b>, <b>картинку</b> или <b>стикер</b>.',
        reply_markup=gpt_keyboard(),
        parse_mode='html'
    )


# ---------------------------------------------------------------------------
# Завершение режима GPT
# ---------------------------------------------------------------------------

@router.callback_query(F.data == 'gpt:stop')
async def on_gpt_stop(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обрабатывает нажатие кнопки 'Закончить' в режиме GPT.
    Очищает состояние, удаляет сообщение с кнопками и возвращает
    пользователя в главное меню.
    """
    try:
        await state.clear()
        await callback.answer('Выхожу из режима ChatGPT')

        try:
            await callback.message.delete()
        except Exception as e:
            logger.warning(f'Не удалось удалить сообщение: {e}')

        await callback.message.answer(
            text='Выбери пункт из меню:',
            reply_markup=main_menu()
        )
        logger.info('Режим GPT успешно завершён.')

    except Exception as e:
        logger.error(f'Критическая ошибка в on_gpt_stop: {e}')
        try:
            await callback.message.answer(
                'Выбери пункт из меню:',
                reply_markup=main_menu()
            )
        except Exception as fallback_error:
            logger.critical(f'Ошибка fallback в on_gpt_stop: {fallback_error}')
            await callback.answer(
                'Критическая ошибка. Используйте /start для возврата в меню.',
                show_alert=True
            )

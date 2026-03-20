"""
Обработчик функции «Помощь с резюме».

FSM States docs:
    https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/index.html

StateFilter docs:
    https://docs.aiogram.dev/en/latest/filters/state.html
"""
import logging
from html import escape
from typing import Any

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.inline import main_menu
from keyboards.resume_keyboard import (
    cancel_keyboard,
    resume_result_keyboard,
    skip_or_cancel_keyboard,
)
from services.openai_service import ask_gpt
from states.state import ResumeStates
from prompts import RESUME_SYSTEM_PROMPT, IMPROVE_PROMPT

router = Router()
logger = logging.getLogger(__name__)

_ANY_RESUME_STATE = StateFilter(ResumeStates)


def _build_resume_prompt(data: dict[str, Any]) -> str:
    """
    Формирует промпт для ChatGPT на основе собранных данных.

    Args:
        data: Словарь FSM-данных с ключами name, position,
              education, experience, skills, additional.

    Returns:
        Готовый промпт для отправки в ChatGPT.
    """
    additional = data.get('additional') or 'не указано'
    name = data.get('name', 'Не указано')
    position = data.get('position', 'Не указано')
    education = data.get('education', 'Не указано')
    experience = data.get('experience', 'Не указано')
    skills = data.get('skills', 'Не указано')

    return (
        'Создай профессиональное резюме на основе следующих данных:\n\n'
        f'👤 ФИО: {name}\n'
        f'💼 Желаемая должность: {position}\n'
        f'🎓 Образование: {education}\n'
        f'📋 Опыт работы: {experience}\n'
        f'🛠 Навыки: {skills}\n'
        f'📝 Дополнительно: {additional}\n\n'
        'Оформи резюме с чёткой структурой разделов. '
        'Текст должен убедительно представлять кандидата работодателю.'
    )


def _split_text(text: str, limit: int = 4096) -> list[str]:
    """
    Разбивает длинный текст на части не более limit символов.

    Старается делать разрыв по символу новой строки.

    Args:
        text: Исходный текст.
        limit: Максимальная длина одного блока (по умолчанию 4096).

    Returns:
        Список строковых блоков.

    Note:
        Telegram ограничивает длину сообщения 4096 символами.
        https://core.telegram.org/bots/api#sendmessage
    """
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        split_pos = text.rfind('\n', 0, limit)
        if split_pos == -1:
            split_pos = limit
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip('\n')
    return parts


async def _generate_and_send_resume(
    message: Message,
    state: FSMContext
) -> None:
    """
    Генерирует резюме через ChatGPT и отправляет пользователю.

    Сохраняет результат в FSM для последующего улучшения.

    Args:
        message: Объект сообщения для ответа.
        state: Контекст FSM с данными пользователя.

    Raises:
        Exception: При ошибке генерации или отправки сообщения.
    """
    wait_msg = await message.answer('⏳ Генерирую резюме, подождите...')
    try:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING
        )
        data = await state.get_data()
        prompt = _build_resume_prompt(data)

        resume_text = await ask_gpt(
            user_message=prompt,
            system_prompt=RESUME_SYSTEM_PROMPT
        )

        await state.update_data(last_resume=resume_text)
        await state.set_state(ResumeStates.showing_result)

        try:
            await wait_msg.delete()
        except Exception:
            pass

        header = '📄 <b>Ваше резюме готово:</b>\n\n'
        chunks = _split_text(header + escape(resume_text), limit=4096)

        for i, chunk in enumerate(chunks):
            kb = resume_result_keyboard() if i == len(chunks) - 1 else None
            await message.answer(chunk, reply_markup=kb, parse_mode='html')

    except Exception as e:
        logger.error('Ошибка генерации резюме: %s', e)
        try:
            await wait_msg.delete()
        except Exception:
            pass
        await message.answer(
            '❌ Не удалось сгенерировать резюме. Попробуйте ещё раз.',
            reply_markup=cancel_keyboard()
        )


# Запуск


@router.message(Command('resume'))
async def cmd_resume(message: Message, state: FSMContext) -> None:
    """
    Обрабатывает команду /resume.

    Сбрасывает предыдущее состояние и запускает сбор данных с шага 1.

    Args:
        message: Объект сообщения с командой.
        state: Контекст FSM для управления состоянием.

    See Also:
        https://docs.aiogram.dev/en/latest/filters/command.html
    """
    try:
        await state.clear()
        await state.set_state(ResumeStates.waiting_name)
        await message.answer(
            '📄 <b>Помощник по составлению резюме</b>\n\n'
            'Я задам несколько вопросов и сформирую готовое резюме.\n\n'
            '1️⃣ из 6 — Введи своё <b>ФИО</b>:',
            reply_markup=cancel_keyboard(),
            parse_mode='html'
        )
    except Exception as e:
        logger.error('Ошибка в cmd_resume: %s', e)
        await message.answer('Произошла ошибка. Попробуйте /resume ещё раз.')


# Шаги сбора данных


@router.message(ResumeStates.waiting_name, F.text)
async def handle_name(message: Message, state: FSMContext) -> None:
    """
    Принимает ФИО и переходит к вопросу о должности.

    Args:
        message: Объект сообщения с текстом ФИО.
        state: Контекст FSM для сохранения данных.
    """
    try:
        await state.update_data(name=message.text.strip())
        await state.set_state(ResumeStates.waiting_position)
        await message.answer(
            '2️⃣ из 6 — Укажи <b>желаемую должность</b>:',
            reply_markup=cancel_keyboard(),
            parse_mode='html'
        )
    except Exception as e:
        logger.error('Ошибка в handle_name: %s', e)
        await message.answer('Ошибка. Введи ФИО ещё раз.')


@router.message(ResumeStates.waiting_position, F.text)
async def handle_position(message: Message, state: FSMContext) -> None:
    """
    Принимает должность и переходит к вопросу об образовании.

    Args:
        message: Объект сообщения с текстом должности.
        state: Контекст FSM для сохранения данных.
    """
    try:
        await state.update_data(position=message.text.strip())
        await state.set_state(ResumeStates.waiting_education)
        await message.answer(
            '3️⃣ из 6 — Расскажи об <b>образовании</b>:\n\n'
            '<i>Учебное заведение, специальность, год окончания</i>',
            reply_markup=cancel_keyboard(),
            parse_mode='html'
        )
    except Exception as e:
        logger.error('Ошибка в handle_position: %s', e)
        await message.answer('Ошибка. Введи должность ещё раз.')


@router.message(ResumeStates.waiting_education, F.text)
async def handle_education(message: Message, state: FSMContext) -> None:
    """
    Принимает образование и переходит к вопросу об опыте работы.

    Args:
        message: Объект сообщения с текстом об образовании.
        state: Контекст FSM для сохранения данных.
    """
    try:
        await state.update_data(education=message.text.strip())
        await state.set_state(ResumeStates.waiting_experience)
        await message.answer(
            '4️⃣ из 6 — Опиши <b>опыт работы</b>:\n\n'
            '<i>Компании, должности, обязанности, достижения.</i>\n'
            '<i>Если опыта нет — так и напиши.</i>',
            reply_markup=cancel_keyboard(),
            parse_mode='html'
        )
    except Exception as e:
        logger.error('Ошибка в handle_education: %s', e)
        await message.answer('Ошибка. Введи образование ещё раз.')


@router.message(ResumeStates.waiting_experience, F.text)
async def handle_experience(message: Message, state: FSMContext) -> None:
    """
    Принимает опыт работы и переходит к вопросу о навыках.

    Args:
        message: Объект сообщения с текстом об опыте работы.
        state: Контекст FSM для сохранения данных.
    """
    try:
        await state.update_data(experience=message.text.strip())
        await state.set_state(ResumeStates.waiting_skills)
        await message.answer(
            '5️⃣ из 6 — Перечисли свои <b>навыки</b>:\n\n'
            '<i>Технические, языковые, личностные (soft skills)</i>',
            reply_markup=cancel_keyboard(),
            parse_mode='html'
        )
    except Exception as e:
        logger.error('Ошибка в handle_experience: %s', e)
        await message.answer('Ошибка. Введи опыт работы ещё раз.')


@router.message(ResumeStates.waiting_skills, F.text)
async def handle_skills(message: Message, state: FSMContext) -> None:
    """
    Принимает навыки и переходит к необязательному шагу.

    Args:
        message: Объект сообщения с текстом о навыках.
        state: Контекст FSM для сохранения данных.
    """
    try:
        await state.update_data(skills=message.text.strip())
        await state.set_state(ResumeStates.waiting_additional)
        await message.answer(
            '6️⃣ из 6 — <b>Дополнительная информация</b> (необязательно):\n\n'
            '<i>Хобби, достижения, рекомендации, портфолио</i>',
            reply_markup=skip_or_cancel_keyboard(),
            parse_mode='html'
        )
    except Exception as e:
        logger.error('Ошибка в handle_skills: %s', e)
        await message.answer('Ошибка. Введи навыки ещё раз.')


@router.message(ResumeStates.waiting_additional, F.text)
async def handle_additional(message: Message, state: FSMContext) -> None:
    """
    Принимает дополнительную информацию и запускает генерацию.

    Args:
        message: Объект сообщения с дополнительной информацией.
        state: Контекст FSM для сохранения данных.
    """
    try:
        await state.update_data(additional=message.text.strip())
        await _generate_and_send_resume(message, state)
    except Exception as e:
        logger.error('Ошибка в handle_additional: %s', e)
        await message.answer(
            '❌ Ошибка при генерации. Попробуйте позже.',
            reply_markup=cancel_keyboard()
        )


# Callback-кнопки


@router.callback_query(
    StateFilter(ResumeStates.waiting_additional),
    F.data == 'resume:skip'
)
async def handle_skip_additional(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """
    Пропускает необязательный шаг и сразу генерирует резюме.

    Args:
        callback: Объект callback-запроса от кнопки «Пропустить».
        state: Контекст FSM для сохранения данных.
    """
    try:
        await callback.answer()
        await state.update_data(additional=None)
        await _generate_and_send_resume(callback.message, state)
    except Exception as e:
        logger.error('Ошибка в handle_skip_additional: %s', e)
        await callback.answer('❌ Ошибка при генерации резюме.', show_alert=True)


@router.callback_query(
    StateFilter(ResumeStates.showing_result),
    F.data == 'resume:improve'
)
async def handle_improve(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """
    Улучшает уже сгенерированное резюме через ChatGPT.

    Использует сохранённый текст из FSM-состояния.

    Args:
        callback: Объект callback-запроса от кнопки «Улучшить».
        state: Контекст FSM с сохранённым резюме.

    Note:
        Если резюме не найдено, состояние сбрасывается.
    """
    try:
        await callback.answer()
        data = await state.get_data()
        last_resume = data.get('last_resume', '')

        if not last_resume:
            await state.clear()
            await callback.answer('Резюме не найдено. Начни заново /resume.', show_alert=True)
            return

        await callback.message.bot.send_chat_action(
            chat_id=callback.message.chat.id,
            action=ChatAction.TYPING
        )

        improve_prompt = f'{IMPROVE_PROMPT}\n\n{last_resume}'

        improved = await ask_gpt(
            user_message=improve_prompt,
            system_prompt=RESUME_SYSTEM_PROMPT
        )

        await state.update_data(last_resume=improved)

        header = '✨ <b>Улучшенное резюме:</b>\n\n'
        chunks = _split_text(header + escape(improved), limit=4096)

        for i, chunk in enumerate(chunks):
            kb = resume_result_keyboard() if i == len(chunks) - 1 else None
            await callback.message.answer(chunk, reply_markup=kb, parse_mode='html')

    except Exception as e:
        logger.error('Ошибка в handle_improve: %s', e)
        await callback.answer('❌ Ошибка при улучшении.', show_alert=True)


@router.callback_query(
    StateFilter(ResumeStates.showing_result),
    F.data == 'resume:restart'
)
async def handle_restart(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """
    Сбрасывает данные и перезапускает сбор информации с шага 1.

    Args:
        callback: Объект callback-запроса от кнопки «Начать заново».
        state: Контекст FSM для сброса данных.
    """
    try:
        await callback.answer()
        await cmd_resume(callback.message, state)
    except Exception as e:
        logger.error('Ошибка в handle_restart: %s', e)
        await callback.answer('❌ Ошибка перезапуска.', show_alert=True)


@router.callback_query(
    _ANY_RESUME_STATE,
    F.data == 'resume:cancel'
)
async def handle_cancel(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """
    Отменяет режим резюме из любого состояния и возвращает в главное меню.

    Args:
        callback: Объект callback-запроса от кнопки «Отмена».
        state: Контекст FSM для сброса состояния.

    See Also:
        https://docs.aiogram.dev/en/latest/filters/state.html#statefilter
    """
    try:
        await state.clear()
        await callback.answer('Выхожу из режима резюме.')
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            'Выбери пункт из меню:',
            reply_markup=main_menu()
        )
    except Exception as e:
        logger.error('Ошибка в handle_cancel: %s', e)
        await callback.answer('❌ Ошибка при отмене.', show_alert=True)


# Заглушка для нетекстовых сообщений


@router.message(StateFilter(ResumeStates))
async def handle_unsupported(message: Message) -> None:
    """
    Перехватывает нетекстовые сообщения в режиме резюме.

    Обрабатывает фото, стикеры, голосовые и другие неподдерживаемые типы,
    предлагая пользователю отправить текст.

    Args:
        message: Объект сообщения с неподдерживаемым типом контента.
    """
    logger.info(
        'Пользователь %s отправил %s в режиме резюме.',
        message.from_user.id,
        message.content_type
    )
    await message.answer(
        '⚠️ Пожалуйста, отвечай <b>текстом</b> — '
        'так я смогу составить резюме.',
        reply_markup=cancel_keyboard(),
        parse_mode='html'
    )

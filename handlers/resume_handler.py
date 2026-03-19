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


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _build_resume_prompt(data: dict[str, Any]) -> str:
    """
    Формирует промпт для ChatGPT на основе собранных данных.

    Args:
        data: словарь FSM-данных с ключами name, position,
              education, experience, skills, additional.

    Returns:
        Готовый промпт для отправки в ChatGPT.
    """
    additional = data.get('additional') or 'не указано'
    return (
        'Создай профессиональное резюме на основе следующих данных:\n\n'
        f'👤 ФИО: {data["name"]}\n'
        f'💼 Желаемая должность: {data["position"]}\n'
        f'🎓 Образование: {data["education"]}\n'
        f'📋 Опыт работы: {data["experience"]}\n'
        f'🛠 Навыки: {data["skills"]}\n'
        f'📝 Дополнительно: {additional}\n\n'
        'Оформи резюме с чёткой структурой разделов. '
        'Текст должен убедительно представлять кандидата работодателю.'
    )


def _split_text(text: str, limit: int = 4096) -> list[str]:
    """
    Разбивает длинный текст на части не более limit символов.
    Старается делать разрыв по символу новой строки.

    Docs Telegram message limit:
    https://core.telegram.org/bots/api#sendmessage

    Args:
        text: исходный текст.
        limit: максимальная длина одного блока.

    Returns:
        Список строковых блоков.
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

    Docs send_chat_action:
    https://core.telegram.org/bots/api#sendchataction

    Args:
        message: объект сообщения для ответа.
        state: контекст FSM с данными пользователя.
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
        logger.error(f'Ошибка генерации резюме: {e}')
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

    Docs:
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
        logger.error(f'Ошибка в cmd_resume: {e}')
        await message.answer('Произошла ошибка. Попробуйте /resume ещё раз.')



# Шаги сбора данных


@router.message(ResumeStates.waiting_name, F.text)
async def handle_name(message: Message, state: FSMContext) -> None:
    """Принимает ФИО и переходит к вопросу о должности."""
    try:
        await state.update_data(name=message.text.strip())
        await state.set_state(ResumeStates.waiting_position)
        await message.answer(
            '2️⃣ из 6 — Укажи <b>желаемую должность</b>:',
            reply_markup=cancel_keyboard(),
            parse_mode='html'
        )
    except Exception as e:
        logger.error(f'Ошибка в handle_name: {e}')
        await message.answer('Ошибка. Введи ФИО ещё раз.')


@router.message(ResumeStates.waiting_position, F.text)
async def handle_position(message: Message, state: FSMContext) -> None:
    """Принимает должность и переходит к вопросу об образовании."""
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
        logger.error(f'Ошибка в handle_position: {e}')
        await message.answer('Ошибка. Введи должность ещё раз.')


@router.message(ResumeStates.waiting_education, F.text)
async def handle_education(message: Message, state: FSMContext) -> None:
    """Принимает образование и переходит к вопросу об опыте работы."""
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
        logger.error(f'Ошибка в handle_education: {e}')
        await message.answer('Ошибка. Введи образование ещё раз.')


@router.message(ResumeStates.waiting_experience, F.text)
async def handle_experience(message: Message, state: FSMContext) -> None:
    """Принимает опыт работы и переходит к вопросу о навыках."""
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
        logger.error(f'Ошибка в handle_experience: {e}')
        await message.answer('Ошибка. Введи опыт работы ещё раз.')


@router.message(ResumeStates.waiting_skills, F.text)
async def handle_skills(message: Message, state: FSMContext) -> None:
    """Принимает навыки и переходит к необязательному шагу."""
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
        logger.error(f'Ошибка в handle_skills: {e}')
        await message.answer('Ошибка. Введи навыки ещё раз.')


@router.message(ResumeStates.waiting_additional, F.text)
async def handle_additional(message: Message, state: FSMContext) -> None:
    """Принимает дополнительную информацию и запускает генерацию."""
    try:
        await state.update_data(additional=message.text.strip())
        await _generate_and_send_resume(message, state)
    except Exception as e:
        logger.error(f'Ошибка в handle_additional: {e}')
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
    """Пропускает необязательный шаг и сразу генерирует резюме."""
    try:
        await callback.answer()
        await state.update_data(additional=None)
        await _generate_and_send_resume(callback.message, state)
    except Exception as e:
        logger.error(f'Ошибка в handle_skip_additional: {e}')
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
    """
    try:
        await callback.answer()
        data = await state.get_data()
        last_resume = data.get('last_resume', '')

        if not last_resume:
            await callback.answer('Резюме не найдено. Начни заново.', show_alert=True)
            return

        await callback.message.bot.send_chat_action(
            chat_id=callback.message.chat.id,
            action=ChatAction.TYPING
        )

        # ✅ ИСПРАВЛЕНО: была строка 'IMPROVE_PROMPT' вместо переменной
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
        logger.error(f'Ошибка в handle_improve: {e}')
        await callback.answer('❌ Ошибка при улучшении.', show_alert=True)


@router.callback_query(
    StateFilter(ResumeStates.showing_result),
    F.data == 'resume:restart'
)
async def handle_restart(
        callback: CallbackQuery,
        state: FSMContext
) -> None:
    """Сбрасывает данные и перезапускает сбор информации с шага 1."""
    try:
        await callback.answer()
        await cmd_resume(callback.message, state)
    except Exception as e:
        logger.error(f'Ошибка в handle_restart: {e}')
        await callback.answer('❌ Ошибка перезапуска.', show_alert=True)


# ✅ ИСПРАВЛЕНО: явный StateFilter(ResumeStates) вместо голого ResumeStates
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

    Docs StateFilter:
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
        logger.error(f'Ошибка в handle_cancel: {e}')
        await callback.answer('❌ Ошибка при отмене.', show_alert=True)


# ---------------------------------------------------------------------------
# Заглушка для нетекстовых сообщений
# ---------------------------------------------------------------------------

# StateFilter(ResumeStates) — все состояния группы, кроме showing_result
# (там пользователь уже не вводит текст)
@router.message(StateFilter(ResumeStates))
async def handle_unsupported(message: Message) -> None:
    """
    Перехватывает нетекстовые сообщения (фото, стикеры, голос и т.д.)
    в режиме резюме и просит ввести текст.
    """
    logger.info(
        f'Пользователь {message.from_user.id} отправил '
        f'{message.content_type} в режиме резюме.'
    )
    await message.answer(
        '⚠️ Пожалуйста, отвечай <b>текстом</b> — '
        'так я смогу составить резюме.',
        reply_markup=cancel_keyboard(),
        parse_mode='html'
    )

import logging
from html import escape
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from states.state import TalkStates
from aiogram.enums import ChatAction
from services.openai_service import ask_gpt
from keyboards.inline import persons_keyboard, talk_keyboard, main_menu
from prompts.persons_prompt import PERSONS

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command('talk'))
async def cmd_talk(message: Message, state: FSMContext):
    """Обрабатывает запуск диалога с известной личностью"""
    await state.set_state(TalkStates.choosing_person)

    try:
        photo = FSInputFile('images/talk.png')
        await message.answer_photo(photo=photo,
                                   caption=(
                                       '<b>Диалог с известной личностью</b>\n\nВыбери с кем хочешь поговорить:'
                                   ), reply_markup=persons_keyboard(PERSONS), parse_mode='html')
    except Exception:
        await message.answer(text='<b>Диалог с известной личностью</b>\n\nВыбери с кем хочешь поговорить:',
                             reply_markup=persons_keyboard(PERSONS))


@router.callback_query(TalkStates.choosing_person, F.data.startswith('talk:person:'))
async def talking_with_person(callback: CallbackQuery, state: FSMContext):
    """Реализует разговор с выбранной личностью"""
    person_key = callback.data.split(':')[-1]

    if person_key not in PERSONS:
        await callback.answer('Неизвестная личность')
        return

    person = PERSONS[person_key]

    await state.update_data(person_key=person_key, history=[])
    await state.set_state(TalkStates.chatting)

    await callback.answer(f'Начинаем разговор с {person["name"]}')

    await callback.message.edit_caption(
        caption=(f'{person["emoji"]} <b>Вы разговариваете с {person["name"]}</b>\n\n'
                 "Напишите что-нибудь - и получите ответ в его стиле"
                 ), reply_markup=talk_keyboard(), parse_mode='html'
    )


@router.callback_query(TalkStates.chatting, F.data.startswith('talk:change'))
async def change_person(callback: CallbackQuery, state: FSMContext):
    """Реализует смену известной личности в диалоге"""
    await cmd_talk(callback.message, state)
    await callback.answer()


@router.callback_query(TalkStates.chatting, F.data == 'talk:stop')
async def stop_talking(callback: CallbackQuery, state: FSMContext):
    """Реализует завершение диалога с известной личностью"""
    try:
        await state.clear()
        await callback.answer('Выхожу из режима "Диалог с известной личностью"',
                              reply_markup=main_menu())
        await callback.message.answer(
            text='Вышел из режима диалога с личностью.\n🔱Выбери какой‑то пункт из меню:',
            reply_markup=main_menu()
        )
        logger.info('Режим "Диалог с известной личностью" успешно завершён.')
    except Exception as e:
        logger.error(f'Критическая ошибка в stop_talking: {e}')
        try:
            await callback.message.answer(
                'Выбери какой‑то пункт из меню:',
                reply_markup=main_menu()
            )
            await callback.answer('Ошибка при завершении режима "Диалог с известной личностью" ', show_alert=True)
        except Exception as fallback_error:
            logger.critical(f'Критическая ошибка при отправке fallback‑сообщения: {fallback_error}')
            await callback.answer(
                'Произошла критическая ошибка. Используйте /start для возврата в меню.',
                show_alert=True
            )


@router.callback_query(TalkStates.choosing_person, F.data == 'talk:cancel')
async def cancel_talk(callback: CallbackQuery, state: FSMContext):
    """Реализует отмену диалога"""
    await stop_talking(callback, state)


@router.message(TalkStates.chatting, F.text)
async def cmd_talk_message(message: Message, state: FSMContext):
    """Реализует разговор с личностью"""
    data = await state.get_data()
    person_key = data['person_key']
    history = data.get('history', [])

    if person_key not in PERSONS:
        await message.answer('Что то пошло не так. Начните заново /talk')
        await state.clear()
        return

    person = PERSONS[person_key]

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING
    )

    history.append({'role': 'user', 'content': message.text})

    response = await ask_gpt(
        user_message=message.text,
        system_prompt=person['prompt'],
        history=history[:-1]
    )

    history.append({'role': 'assistant', 'content': response})

    if len(history) > 16:
        history = history[-16:]

    await state.update_data(history=history)

    await message.answer(
        f'{person["emoji"]} <b>{escape(person["name"])}</b>\n\n{escape(response)}',
        reply_markup=talk_keyboard()
    )

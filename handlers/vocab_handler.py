import logging

from aiogram import Router, F
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.inline import main_menu, vocab_actions_keyboard
from states.state import VocabStates
from utils.vocab_generate import check_translation, generate_word

router = Router()
logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = 'английский'

@router.message(Command('vocab'))
async def cmd_vocab(message: Message, state: FSMContext) -> None:
    """Запуск словарного тренажёра командой /vocab."""
    await state.set_state(VocabStates.learning)
    await state.update_data(
        learned_words=[],
        language=DEFAULT_LANGUAGE
    )

    await message.answer(
        '📚 <b>Словарный тренажёр</b>\n\n'
        'Я буду присылать тебе новые слова с переводом и примерами.\n'
        'Когда выучишь несколько слов — нажми <b>🎯 Тренироваться</b>!'
    )
    await send_new_word(message, state)


async def send_new_word(message: Message, state: FSMContext) -> None:
    """Генерирует и отправляет новое слово пользователю."""
    data = await state.get_data()
    learned_words: list[dict] = data.get('learned_words', [])
    language: str = data.get('language', DEFAULT_LANGUAGE)

    used = [w['word'] for w in learned_words]

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING
    )

    word_data = await generate_word(language=language, used_words=used)

    if not word_data:
        await message.answer(
            '❌ Не удалось получить слово. Попробуй ещё раз.',
            reply_markup=vocab_actions_keyboard(has_words=bool(learned_words))
        )
        return

    # Слово считается выученным сразу после отправки
    learned_words.append(word_data)
    await state.update_data(learned_words=learned_words)

    transcription = word_data.get('transcription', '')
    transcription_str = f' [{transcription}]' if transcription else ''

    examples = word_data.get('examples', [])
    examples_text = '\n'.join(f'  • {ex}' for ex in examples)

    text = (
        f'📖 <b>Новое слово</b>\n\n'
        f'🔤 <b>{word_data["word"]}</b>{transcription_str}\n'
        f'🇷🇺 <i>{word_data["translation"]}</i>\n\n'
        f'<b>Примеры использования:</b>\n{examples_text}\n\n'
        f'📚 Выучено слов: <b>{len(learned_words)}</b>'
    )

    await message.answer(
        text,
        reply_markup=vocab_actions_keyboard(has_words=True)
    )


async def send_train_word(message: Message, state: FSMContext) -> None:
    """Отправляет очередное слово в режиме тренировки."""
    data = await state.get_data()
    train_words: list[dict] = data.get('train_words', [])
    train_index: int = data.get('train_index', 0)

    if train_index >= len(train_words):
        await finish_training(message, state)
        return

    word_data = train_words[train_index]
    total = len(train_words)

    await message.answer(
        f'<b>Слово {train_index + 1} из {total}</b>\n\n'
        f'🔤 <b>{word_data["word"]}</b>\n\n'
        f'Переведи это слово на русский:'
    )


async def finish_training(message: Message, state: FSMContext) -> None:
    """Завершает тренировку и показывает итоговый результат."""
    data = await state.get_data()
    score: int = data.get('train_score', 0)
    total: int = len(data.get('train_words', []))

    if total == 0:
        verdict = 'Не удалось провести тренировку.'
    elif score == total:
        verdict = '🏆 Идеальный результат!'
    elif score / total >= 0.75:
        verdict = '🎉 Шикарная работа!'
    elif score / total >= 0.4:
        verdict = '📈 Неплохо, продолжай учиться!'
    else:
        verdict = '📚 Стоит ещё поучить слова!'

    # Возвращаемся в режим изучения — слова не сбрасываем
    await state.set_state(VocabStates.learning)
    await state.update_data(train_index=0, train_score=0, train_words=[])

    await message.answer(
        f'🎓 <b>Тренировка завершена!</b>\n\n'
        f'Правильных ответов: <b>{score} из {total}</b>\n\n'
        f'{verdict}',
        reply_markup=vocab_actions_keyboard(has_words=True)
    )


@router.callback_query(VocabStates.learning, F.data == 'vocab:next')
async def on_vocab_next(callback: CallbackQuery, state: FSMContext) -> None:
    """Следующее слово в режиме изучения."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await send_new_word(callback.message, state)


@router.callback_query(VocabStates.learning, F.data == 'vocab:train')
async def on_vocab_train(callback: CallbackQuery, state: FSMContext) -> None:
    """Запуск тренировки по выученным словам."""
    data = await state.get_data()
    learned_words: list[dict] = data.get('learned_words', [])

    if not learned_words:
        await callback.answer(
            'Сначала выучи хотя бы одно слово!',
            show_alert=True
        )
        return

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    await state.set_state(VocabStates.training)
    await state.update_data(
        train_words=learned_words.copy(),
        train_index=0,
        train_score=0
    )

    await callback.message.answer(
        f'🎯 <b>Тренировка начинается!</b>\n\n'
        f'Всего слов: <b>{len(learned_words)}</b>\n'
        f'Переводи каждое слово на русский язык.\n\n'
        f'Поехали! 🚀'
    )
    await send_train_word(callback.message, state)


@router.message(VocabStates.training, F.text)
async def on_train_answer(message: Message, state: FSMContext) -> None:
    """Обработка ответа пользователя в режиме тренировки."""
    data = await state.get_data()
    train_words: list[dict] = data.get('train_words', [])
    train_index: int = data.get('train_index', 0)
    train_score: int = data.get('train_score', 0)

    if train_index >= len(train_words):
        await finish_training(message, state)
        return

    word_data = train_words[train_index]

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING
    )

    is_correct, explanation = await check_translation(
        word=word_data['word'],
        user_answer=message.text,
        correct_translation=word_data['translation']
    )

    new_index = train_index + 1
    new_score = train_score + (1 if is_correct else 0)

    await state.update_data(train_index=new_index, train_score=new_score)

    result_header = '✅ <b>Верно!</b>' if is_correct else '⛔️ <b>Неверно</b>'
    remaining = len(train_words) - new_index
    remaining_str = (
        f'\n\n⏭ Осталось слов: <b>{remaining}</b>'
        if remaining > 0 else ''
    )

    await message.answer(
        f'{result_header}\n\n'
        f'{explanation}\n\n'
        f'✏️ Правильный перевод: <b>{word_data["translation"]}</b>\n'
        f'📊 Счёт: <b>{new_score}/{new_index}</b>'
        f'{remaining_str}'
    )

    if new_index >= len(train_words):
        await finish_training(message, state)
    else:
        await send_train_word(message, state)


@router.callback_query(VocabStates.learning, F.data == 'vocab:stop')
async def on_vocab_stop(callback: CallbackQuery, state: FSMContext) -> None:
    """Завершение словарного тренажёра."""
    data = await state.get_data()
    learned_words: list[dict] = data.get('learned_words', [])
    count = len(learned_words)

    await state.clear()
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f'👋 <b>Тренажёр завершён</b>\n\n'
        f'За эту сессию ты выучил <b>{count}</b> '
        f'{"слово" if count == 1 else "слова" if 2 <= count <= 4 else "слов"}.\n'
        f'Возвращайся за новыми словами! 📚',
        reply_markup=main_menu()
    )

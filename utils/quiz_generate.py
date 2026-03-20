from html import escape

from aiogram.enums import ChatAction

from services.openai_service import ask_gpt
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from prompts.topics import TOPICS


async def generate_answer(topic_key: str, TOPICS: dict) -> str:
    topic = TOPICS[topic_key]
    prompt = (
        f'Ты ведущий квиза. Задай один интересный вопрос по теме: {topic["prompt_name"]}. '
        'Вопрос должен иметь четкий и однозначный ответ из одного слова. '
        'Напиши только сам вопрос, без нумерации и без ответа.'
    )

    return await ask_gpt(user_message=prompt)


async def check_answer(question: str, user_answer: str) -> tuple[bool, str]:
    """
    Отправляет вопрос + ответ в GPT для проверки
    Возвращает (is_correct: bool, answer)
    :param question:
    :param user_answer:
    :return:
    """
    prompt = (
        f'Вопрос квиза: {question}\n'
        f'Ответ пользователя: {user_answer}\n\n'
        'Оцени правильность ответа. Отвечай строго в таком формате.\n'
        'Первая строка: только слово ВЕРНО или только слово НЕВЕРНО.\n'
        'Вторая строка и далее: краткое объяснение (1-2 предложения),'
        ' и если ответ неверный - укажи правильный ответ.'
    )
    response = await ask_gpt(user_message=prompt)

    lines = response.strip().split('\n')
    first_line = lines[0].strip().upper()

    is_correct = first_line.startswith('ВЕРНО')

    explanation = '\n'.join(lines[1:]).strip()

    if not explanation:
        explanation = 'Засчитано' if is_correct else 'Неправильно'

    return is_correct, explanation


async def send_next_question(message: Message, state: FSMContext, topic_key: str):
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING
    )

    question = await generate_answer(topic_key=topic_key, TOPICS=TOPICS)
    await state.update_data(current_question=question)
    data = await state.get_data()
    score = data.get('score', 0)
    total = data.get('total', 0)
    topic_name = TOPICS[topic_key]['name']

    await message.answer(
        f'Счет <b>{score}/{total}</b> | Тема <b>{escape(topic_name)}</b>\n\n'
        f'<b>Вопрос</b>\n{escape(question)}'
    )

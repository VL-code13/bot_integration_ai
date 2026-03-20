import base64
import logging
from typing import Any

from aiogram.fsm.context import FSMContext
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, MODEL
from aiogram.types import Message

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
logger = logging.getLogger(__name__)


# Вспомогательные функции
# Читаемые названия неподдерживаемых типов для сообщения пользователю
UNSUPPORTED_TYPES: dict[str, str] = {
    'voice': '🎤 голосовое сообщение',
    'video': '🎥 видео',
    'video_note': '📹 видеосообщение',
    'document': '📄 документ',
    'audio': '🎵 аудио',
    'location': '📍 геолокацию',
    'contact': '👤 контакт',
    'poll': '📊 опрос',
}


async def download_photo_as_base64(message: Message) -> str | None:
    """
    Скачивает фото из сообщения и возвращает его в формате base64.

    Args:
        message: сообщение Telegram, содержащее фото.

    Returns:
        Строка base64 или None при ошибке.
    """
    try:
        # Берём фото с максимальным разрешением (последний элемент списка)
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        return base64.b64encode(file_bytes.read()).decode('utf-8')
    except Exception as e:
        logger.error(f'Ошибка при загрузке фото: {e}')
        return None


def get_unsupported_type_name(message: Message) -> str:
    """
    Определяет тип неподдерживаемого контента из сообщения.

    Args:
        message: сообщение Telegram с неизвестным типом контента.

    Returns:
        Читаемое название типа контента на русском языке.
    """
    content_type = message.content_type.value
    return UNSUPPORTED_TYPES.get(content_type, f'тип «{content_type}»')


async def update_history(
        state: FSMContext,
        user_content: str,
        assistant_response: str,
        max_history: int = 20
) -> None:
    """
    Добавляет реплику пользователя и ответ ассистента в историю диалога.
    Обрезает историю до max_history последних сообщений.

    Args:
        state: контекст FSM для хранения истории.
        user_content: текст запроса пользователя.
        assistant_response: ответ ChatGPT.
        max_history: максимальное количество хранимых сообщений.
    """
    data = await state.get_data()
    history: list[dict] = data.get('history', [])
    history.append({'role': 'user', 'content': user_content})
    history.append({'role': 'assistant', 'content': assistant_response})
    if len(history) > max_history:
        history = history[-max_history:]
    await state.update_data(history=history)


def _normalize_text(value: Any) -> str:
    """
    Приводит произвольное значение к строке.
    Рекурсивно обходит списки и кортежи, конкатенируя элементы.

    Args:
        value: любое значение — строка, список, кортеж, None или другое.

    Returns:
        Строковое представление значения.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ''.join(_normalize_text(item) for item in value)
    if value is None:
        return ''
    return str(value)


def _build_valid_history(
    history: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Фильтрует и нормализует историю диалога перед отправкой в OpenAI.
    Пропускает элементы без обязательных ключей 'role' и 'content'.

    Args:
        history: сырая история сообщений из FSM-состояния.

    Returns:
        Список корректных сообщений для передачи в ChatGPT.
    """
    result = []
    for item in history:
        if not isinstance(item, dict):
            continue
        if 'role' not in item or 'content' not in item:
            continue
        # Если content — список (vision-сообщение), оставляем как есть,
        # иначе нормализуем до строки
        content = (
            item['content']
            if isinstance(item['content'], list)
            else _normalize_text(item['content'])
        )
        result.append({'role': item['role'], 'content': content})
    return result


async def ask_gpt(
    user_message: Any,
    system_prompt: Any = 'Ты полезный ассистент. Отвечай кратко и по делу.',
    history: list[dict[str, Any]] | None = None
) -> str:
    """
    Отправляет текстовый запрос в ChatGPT с учётом истории диалога.

    Args:
        user_message: сообщение пользователя (строка или приводимый тип).
        system_prompt: системный промпт для настройки поведения модели.
        history: список предыдущих сообщений диалога в формате
                 [{'role': ..., 'content': ...}, ...].

    Returns:
        Текстовый ответ от ChatGPT или сообщение об ошибке.
    """
    try:
        system_text = _normalize_text(system_prompt)
        user_text = _normalize_text(user_message)

        messages: list[dict[str, Any]] = [
            {'role': 'system', 'content': system_text}
        ]

        if history:
            messages.extend(_build_valid_history(history))

        messages.append({'role': 'user', 'content': user_text})
        logger.info(f'GPT запрос: {user_text[:120]}')

        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.8
        )

        answer = response.choices[0].message.content or ''
        logger.info(f'Ответ GPT: {len(answer)} символов')
        return answer

    except Exception as e:
        logger.error(f'Ошибка ask_gpt: {e}')
        return 'Ошибка при обращении к GPT. Попробуй ещё раз.'


async def ask_gpt_vision(
    image_base64: str,
    user_text: str,
    system_prompt: str = 'Ты полезный ассистент. Отвечай кратко и по делу.',
    history: list[dict[str, Any]] | None = None
) -> str:
    """
    Отправляет изображение (base64) и текстовый запрос в GPT Vision.

    Args:
        image_base64: изображение, закодированное в base64.
        user_text: текстовый вопрос или подпись к изображению.
        system_prompt: системный промпт для настройки поведения модели.
        history: список предыдущих сообщений диалога в формате
                 [{'role': ..., 'content': ...}, ...].

    Returns:
        Текстовый ответ от ChatGPT или сообщение об ошибке.
    """
    try:
        messages: list[dict[str, Any]] = [
            {'role': 'system', 'content': system_prompt}
        ]

        if history:
            messages.extend(_build_valid_history(history))

        messages.append({
            'role': 'user',
            'content': [
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:image/jpeg;base64,{image_base64}'
                    }
                },
                {
                    'type': 'text',
                    'text': user_text
                }
            ]
        })

        logger.info(f'GPT Vision запрос: {user_text[:120]}')

        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.8
        )

        answer = response.choices[0].message.content or ''
        logger.info(f'Ответ GPT Vision: {len(answer)} символов')
        return answer

    except Exception as e:
        logger.error(f'Ошибка ask_gpt_vision: {e}')
        return 'Не удалось обработать изображение. Попробуйте позже.'

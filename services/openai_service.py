import logging
from typing import Any

from openai import AsyncOpenAI

from config import OPENAI_API_KEY


client = AsyncOpenAI(api_key=OPENAI_API_KEY)
MODEL = 'gpt-4o-mini'


logger = logging.getLogger(__name__)


def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ''.join(_normalize_text(item) for item in value)
    if value is None:
        return ''
    return str(value)


async def ask_gpt(
        user_message: Any,
        system_prompt: Any = 'Ты полезный ассистент.Отвечай кратко и по делу',
        history: list[dict[str, Any]] | None = None
) -> str:
    try:
        system_text = _normalize_text(system_prompt)
        user_text = _normalize_text(user_message)

        messages = [{'role': 'system', 'content': system_text}]

        if history:
            valid_history = [
                {
                    'role': item['role'],
                    'content': _normalize_text(item['content'])
                }
                for item in history
                if isinstance(item, dict) and 'role' in item and 'content' in item
            ]
            messages.extend(valid_history)
        messages.append({'role': 'user', 'content': user_text})
        logger.info(f'GPT запрос {user_text[:120]}')

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
        logger.error(f'Ошибка GPT {e}')
        return 'Ошибка при обращении к GPT. Попробуй еще раз'

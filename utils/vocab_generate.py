import json
import logging

from openai import AsyncOpenAI

from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def generate_word(
    language: str = 'английский',
    used_words: list[str] | None = None
) -> dict | None:
    """
    Генерирует новое иностранное слово с переводом и примерами через ChatGPT.

    Args:
        language: язык, слово которого нужно сгенерировать.
        used_words: список уже использованных слов для исключения повторов.

    Returns:
        Словарь с ключами 'word', 'translation', 'transcription', 'examples'
        или None в случае ошибки.
    """
    if used_words is None:
        used_words = []

    exclude_str = (
        f'Исключи слова: {", ".join(used_words)}.'
        if used_words else ''
    )

    prompt = (
        f'Ты — языковой тренажёр. Дай одно случайное {language} слово уровня A2–B1.\n'
        f'{exclude_str}\n'
        f'Ответь строго в формате JSON (без markdown, без ```):\n'
        '{\n'
        f'  "word": "слово на {language}",\n'
        '  "translation": "перевод на русский",\n'
        '  "transcription": "транскрипция",\n'
        '  "examples": [\n'
        f'    "пример на {language} — перевод на русский",\n'
        f'    "пример на {language} — перевод на русский"\n'
        '  ]\n'
        '}'
    )

    try:
        response = await client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f'Ошибка парсинга JSON при генерации слова: {e}')
        return None
    except Exception as e:
        logger.error(f'Ошибка генерации слова: {e}')
        return None


async def check_translation(
    word: str,
    user_answer: str,
    correct_translation: str
) -> tuple[bool, str]:
    """
    Проверяет правильность перевода слова через ChatGPT.
    Учитывает синонимы и близкие по значению варианты.

    Args:
        word: исходное иностранное слово.
        user_answer: перевод, введённый пользователем.
        correct_translation: эталонный перевод слова.

    Returns:
        Кортеж (is_correct, explanation), где:
            - is_correct: True если перевод верный, False если нет.
            - explanation: пояснение от ChatGPT.
    """
    prompt = (
        f'Слово: "{word}"\n'
        f'Правильный перевод: "{correct_translation}"\n'
        f'Ответ пользователя: "{user_answer}"\n\n'
        'Оцени правильность перевода. Учитывай синонимы '
        'и близкие по значению слова.\n'
        'Ответь строго в формате JSON (без markdown, без ```):\n'
        '{\n'
        '  "is_correct": true,\n'
        '  "explanation": "краткий комментарий"\n'
        '}'
    )

    try:
        response = await client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        result = json.loads(content)
        return result['is_correct'], result['explanation']
    except json.JSONDecodeError as e:
        logger.error(f'Ошибка парсинга JSON при проверке перевода: {e}')
        return False, 'Не удалось проверить ответ.'
    except Exception as e:
        logger.error(f'Ошибка проверки перевода: {e}')
        return False, 'Не удалось проверить ответ.'

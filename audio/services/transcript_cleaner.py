import re
from typing import List

class TranscriptCleaner:
    """
    Очистка шумного русского транскрипта Whisper для последующей подачи в LLM.
    """

    # Список фраз/слов, которые почти всегда являются шумом в защите проекта
    NOISE_PHRASES = {
        "хорошо", "конечно", "ну", "вот", "да", "нет", "спасибо", "ещё вопрос",
        "вопросы у вас есть", "держите", "подожди", "гориться", "слайду", "включите",
        "переходим к хорошим", "это убийство да", "не будем угробляться", "понятно",
        "хорошо спасибо", "все осадитесь пожалуйста", "мужики", "чуть-чуть"
    }

    @staticmethod
    def clean(transcript: str, min_words: int = 4) -> str:
        if not transcript:
            return ""

        # Разбиваем на предложения
        sentences = re.split(r'[.!?]+', transcript)
        cleaned_sentences: List[str] = []

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue

            # Приводим к нижнему регистру для проверки шума
            lower_sent = sent.lower()

            # Пропускаем короткие предложения
            words = lower_sent.split()
            if len(words) < min_words:
                continue

            # Пропускаем предложения, которые полностью состоят из шума
            if any(noise in lower_sent for noise in TranscriptCleaner.NOISE_PHRASES):
                # Дополнительная проверка: если предложение слишком короткое и содержит шум — удаляем
                if len(words) <= 8:
                    continue

            # Убираем лишние повторы (например, "да да да")
            sent = re.sub(r'\b(\w+)\s+\1\b', r'\1', sent)

            # Нормализация пробелов и пунктуации
            sent = re.sub(r'\s+', ' ', sent).strip()
            sent = re.sub(r'([.!?])\1+', r'\1', sent)  # убираем !!!

            if sent and len(sent.split()) >= min_words:
                cleaned_sentences.append(sent)

        result = '. '.join(cleaned_sentences) + '.'
        return re.sub(r'\s+', ' ', result).strip()

# Удобная функция для вызова из tasks.py
def clean_transcription(transcript: str) -> str:
    cleaner = TranscriptCleaner()
    return cleaner.clean(transcript, min_words=4) 